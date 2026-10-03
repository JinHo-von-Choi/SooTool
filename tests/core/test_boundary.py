from __future__ import annotations

import asyncio
import decimal
import inspect
from typing import Any

import pytest

from sootool import server as S
from sootool.boundary import (
    INTERNAL_ERROR_CODE,
    coerced_signature,
    error_payload,
    error_result,
    with_error_contract,
)
from sootool.core import errors as E
from sootool.core.registry import REGISTRY


@pytest.fixture(scope="module")
def srv():
    S._load_modules()
    return S.build_server()


def _call(srv, name: str, args: dict[str, Any]):
    return asyncio.run(srv.call_tool(name, args))


# --- 오류 계약 ---

@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (E.InvalidInputError("x"), "invalid_input"),
        (E.InvalidNumberError("x"), "invalid_number"),
        (E.FloatInputError("x"), "float_input"),
        (E.DomainConstraintError("x"), "domain_constraint"),
        (E.DivisionByZeroError("x"), "division_by_zero"),
        (E.PrecisionLossError("x"), "precision_loss"),
        (E.UnsafeDirectoryError("x"), "unsafe_directory"),
        (E.ToolTimeoutError("t", 1.5), "timeout"),
        (E.InputLimitError("n", 5, 9), "input_limit"),
        (E.InvalidExpressionError("bad", (1, 2)), "invalid_expression"),
        (E.DisallowedOperationError("Call"), "disallowed_operation"),
        (E.UndefinedVariableError("x"), "undefined_variable"),
        (E.ExpressionTooComplexError("nodes", 10, 20), "expression_too_complex"),
    ],
)
def test_every_error_class_has_its_own_code(exc, code):
    assert error_payload(exc)["code"] == code


def test_error_codes_are_unique_per_class():
    classes = [
        c for c in vars(E).values()
        if isinstance(c, type) and issubclass(c, E.SooToolError)
    ]
    codes = {c.code for c in classes}
    assert len(codes) == len(classes)


def test_payload_carries_field_details_and_retryable():
    payload = error_payload(E.InputLimitError("n", 5, 9))
    assert payload["field"] == "n"
    assert payload["details"] == {"limit": 5, "observed": 9}
    assert payload["retryable"] is False
    assert error_payload(E.ToolTimeoutError("t", 2))["retryable"] is True


def test_compatibility_with_standard_exceptions():
    assert issubclass(E.InvalidNumberError, decimal.InvalidOperation)
    assert issubclass(E.FloatInputError, TypeError)
    assert issubclass(E.DivisionByZeroError, ZeroDivisionError)


def test_unexpected_exception_becomes_internal_error_without_leaking_message():
    payload = error_payload(RuntimeError("secret path /etc/passwd"))
    assert payload["code"] == INTERNAL_ERROR_CODE
    assert "secret" not in payload["message"]
    assert payload["details"] == {"type": "RuntimeError"}


def test_error_result_is_an_is_error_call_result():
    result = error_result(E.InvalidInputError("bad"))
    assert result.is_error is True
    assert result.content[0].text == "[invalid_input] bad"
    assert result.structured_content["error"]["code"] == "invalid_input"


def test_contract_wrapper_converts_exceptions_and_logs_unexpected(caplog):
    def tool(n: str) -> dict[str, Any]:
        raise ValueError("boom")

    wrapped = with_error_contract(tool)
    with caplog.at_level("ERROR", logger="sootool.boundary"):
        result = wrapped(n="1")
    assert result.structured_content["error"]["code"] == INTERNAL_ERROR_CODE
    assert any("unexpected error" in r.message for r in caplog.records)


def test_non_numeric_strings_yield_invalid_number_over_mcp(srv):
    result = _call(srv, "core.add", {"operands": ["1,000"]})
    assert result.is_error is True
    error = result.structured_content["error"]
    assert error["code"] == "invalid_number"
    assert "1,000" in error["message"]


def test_division_by_zero_over_mcp(srv):
    result = _call(srv, "core.div", {"a": "1", "b": "0"})
    assert result.structured_content["error"]["code"] == "division_by_zero"


def test_unavailable_policy_year_is_typed_over_mcp(srv):
    result = _call(srv, "tax.kr_income", {"taxable_income": "1000000", "year": 1999})
    error = result.structured_content["error"]
    assert error["code"] == "policy_unavailable"
    assert error["details"]["year"] == 1999


# --- 입력 숫자 허용 ---

def test_json_numbers_are_accepted_for_string_parameters(srv):
    result = _call(srv, "core.add", {"operands": [1, 2.5, "3"]})
    assert result.is_error is False
    assert result.structured_content["result"] == "6.5"


def test_json_numbers_are_accepted_inside_dict_values(srv):
    result = _call(srv, "core.calc", {"expression": "x*2", "variables": {"x": 1.5}})
    assert result.structured_content["result"] == "3.0"


def test_large_integers_keep_all_digits(srv):
    big = 12345678901234567890123
    result = _call(srv, "core.add", {"operands": [big, 1]})
    assert result.structured_content["result"] == str(big + 1)


def test_float_uses_shortest_roundtrip_representation(srv):
    result = _call(srv, "core.add", {"operands": [0.1, 0.2]})
    assert result.structured_content["result"] == "0.3"


def test_booleans_are_not_treated_as_numbers(srv):
    result = _call(srv, "core.add", {"operands": [True]})
    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "invalid_arguments"


# --- SDK 단계에서 거부되는 입력도 같은 계약을 따른다 ---

def test_missing_required_argument_follows_contract(srv):
    result = _call(srv, "core.add", {})
    error = result.structured_content["error"]
    assert result.is_error is True
    assert error["code"] == "invalid_arguments"
    assert error["details"]["problems"] == [{"field": "operands", "message": "Field required"}]


def test_wrong_argument_type_reports_the_field_path_without_echoing_the_value(srv):
    result = _call(srv, "core.add", {"operands": "not-a-list-SECRET"})
    error = result.structured_content["error"]
    assert error["code"] == "invalid_arguments"
    assert error["details"]["problems"][0]["field"] == "operands"
    assert "SECRET" not in str(error)


def test_unknown_tool_follows_contract(srv):
    result = _call(srv, "core.nope", {})
    error = result.structured_content["error"]
    assert error["code"] == "unknown_tool"
    assert error["details"]["name"] == "core.nope"


def test_undeclared_arguments_are_rejected_not_silently_dropped(srv):
    result = _call(srv, "core.sub", {"a": "1", "b": "2", "rouding": "UP"})
    error = result.structured_content["error"]
    assert error["code"] == "invalid_arguments"
    assert error["details"]["problems"] == [{"field": "rouding", "message": "Unexpected argument"}]


def test_misspelled_optional_argument_cannot_change_a_result_silently(srv):
    """오타 난 반올림 인자가 무시되어 기본 정책으로 계산되는 일이 없어야 한다."""
    ok  = _call(srv, "tax.progressive", {
        "taxable_income": "1000", "brackets": [{"upper": None, "rate": "0.333"}], "rounding": "DOWN",
    })
    bad = _call(srv, "tax.progressive", {
        "taxable_income": "1000", "brackets": [{"upper": None, "rate": "0.333"}], "roundin": "DOWN",
    })
    assert ok.is_error is False
    assert bad.is_error is True


def test_advertised_input_schema_still_says_string(srv):
    tools = {t.name: t for t in asyncio.run(srv.list_tools())}
    items = tools["core.add"].input_schema["properties"]["operands"]["items"]
    assert items == {"type": "string"}


def test_coerced_signature_keeps_parameter_names_and_defaults():
    entry = next(e for e in REGISTRY.list() if e.full_name == "finance.loan_schedule")
    original = inspect.signature(entry.fn)
    coerced  = coerced_signature(entry.fn)
    assert list(coerced.parameters) == list(original.parameters)
    assert [p.default for p in coerced.parameters.values()] == [p.default for p in original.parameters.values()]


def test_every_tool_signature_resolves_for_coercion():
    """타입 힌트를 해석하지 못하는 도구가 있으면 숫자 허용이 조용히 빠지므로 전수 확인한다."""
    S._load_modules()
    unresolved = []
    for entry in REGISTRY.list():
        import typing
        try:
            typing.get_type_hints(entry.fn)
        except Exception:  # noqa: BLE001
            unresolved.append(entry.full_name)
    assert not unresolved, unresolved


# --- 전수 오류 형식 ---

_SKIP = {
    "core.batch", "core.pipeline", "core.pipeline_resume", "sootool.verify_receipt",
    "sootool.policy_activate", "sootool.policy_rollback", "sootool.policy_import", "sootool.policy_propose",
}


def _bad_value(annotation: str) -> Any:
    a = annotation.replace(" ", "")
    if a.startswith("list[list[str]]"):
        return [["abc"]]
    if a.startswith("list[dict"):
        return [{"x": "abc"}]
    if a.startswith("list[int]"):
        return [-1]
    if a.startswith("list[str]"):
        return ["abc"]
    if a.startswith("dict"):
        return {"x": "abc"}
    if a.startswith("int"):
        return -5
    if a.startswith("float"):
        return -1.0
    return "abc"


def test_invalid_inputs_never_raise_untyped_exceptions_from_any_tool():
    """모든 도구가 잘못된 입력에 SooToolError 만 낸다(날 예외는 오류 계약 위반)."""
    S._load_modules()
    untyped: list[tuple[str, str]] = []
    for entry in REGISTRY.list():
        if entry.full_name in _SKIP:
            continue
        kwargs = {
            p.name: _bad_value(str(p.annotation))
            for p in inspect.signature(entry.fn).parameters.values()
            if p.default is inspect.Parameter.empty
        }
        try:
            REGISTRY.invoke(entry.full_name, **kwargs)
        except E.SooToolError:
            pass
        except Exception as exc:  # noqa: BLE001
            untyped.append((entry.full_name, type(exc).__name__))
    assert not untyped, untyped
