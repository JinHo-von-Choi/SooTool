"""core.calc security boundary, numeric correctness, DoS defense tests.

ADR-017 implementation verification.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from sootool.core.calc import calc
from sootool.core.errors import (
    DisallowedOperationError,
    DomainConstraintError,
    ExpressionTooComplexError,
    InvalidExpressionError,
    UndefinedVariableError,
)

# ---------------------------------------------------------------------------
# whitelist — 50+ malicious inputs
# ---------------------------------------------------------------------------

_MALICIOUS_CASES: list[tuple[str, type[Exception]]] = [
    ("__import__('os')",                                DisallowedOperationError),
    ("__import__('os').system('ls')",                   DisallowedOperationError),
    ("open('/etc/passwd')",                             DisallowedOperationError),
    ("eval('1+1')",                                     DisallowedOperationError),
    ("exec('1')",                                       DisallowedOperationError),
    ("compile('1', '<s>', 'eval')",                     DisallowedOperationError),
    ("globals()",                                       DisallowedOperationError),
    ("locals()",                                        DisallowedOperationError),
    ("getattr(x, 'foo')",                               DisallowedOperationError),
    ("setattr(x, 'foo', 1)",                            DisallowedOperationError),
    ("vars()",                                          DisallowedOperationError),
    ("dir()",                                           DisallowedOperationError),
    ("type(1)",                                         DisallowedOperationError),
    ("help()",                                          DisallowedOperationError),
    ("().__class__",                                    DisallowedOperationError),
    ("().__class__.__bases__",                          DisallowedOperationError),
    ("x.__class__",                                     DisallowedOperationError),
    ("x.__dict__",                                      DisallowedOperationError),
    ("x.real",                                          DisallowedOperationError),
    ("x[0]",                                            DisallowedOperationError),
    ("x[0:1]",                                          DisallowedOperationError),
    ("x[0][1]",                                         DisallowedOperationError),
    ("(1).bit_length()",                                DisallowedOperationError),
    ("[x for x in range(10)]",                          DisallowedOperationError),
    ("{x for x in range(10)}",                          DisallowedOperationError),
    ("{x: x for x in range(3)}",                        DisallowedOperationError),
    ("(x for x in range(10))",                          DisallowedOperationError),
    ("lambda x: x+1",                                   DisallowedOperationError),
    ("1 and 2",                                         DisallowedOperationError),
    ("1 or 2",                                          DisallowedOperationError),
    ("not 1",                                           DisallowedOperationError),
    ("1 < 2",                                           DisallowedOperationError),
    ("1 == 1",                                          DisallowedOperationError),
    ("1 if 2 else 3",                                   DisallowedOperationError),
    ("(x := 1)",                                        DisallowedOperationError),
    ("f'{x}'",                                          DisallowedOperationError),
    ("[1, 2, 3]",                                       DisallowedOperationError),
    ("{1, 2, 3}",                                       DisallowedOperationError),
    ("{'a': 1}",                                        DisallowedOperationError),
    ("*x",                                              InvalidExpressionError),
    ("await x",                                         DisallowedOperationError),
    ("hex(255)",                                        DisallowedOperationError),
    ("oct(8)",                                          DisallowedOperationError),
    ("bin(5)",                                          DisallowedOperationError),
    ("input()",                                         DisallowedOperationError),
    ("print(1)",                                        DisallowedOperationError),
    ("len('abc')",                                      DisallowedOperationError),
    ("range(10)",                                       DisallowedOperationError),
    ("id(1)",                                           DisallowedOperationError),
    ("hash(1)",                                         DisallowedOperationError),
    ("SQRT(4)",                                         DisallowedOperationError),
    ("Sqrt(4)",                                         DisallowedOperationError),
    ("sqrt_(4)",                                        DisallowedOperationError),
    ("sqrt(x=4)",                                       DisallowedOperationError),
    ("(lambda x: x)(1)",                                DisallowedOperationError),
    ("'abc'",                                           DisallowedOperationError),
    ("b'abc'",                                          DisallowedOperationError),
    ("1 +",                                             InvalidExpressionError),
    ("(1 + 2",                                          InvalidExpressionError),
    ("1 ** ",                                           InvalidExpressionError),
    ("True",                                            DisallowedOperationError),
    ("False",                                           DisallowedOperationError),
    ("None",                                            DisallowedOperationError),
]


@pytest.mark.parametrize("expression,exc", _MALICIOUS_CASES)
def test_malicious_input_rejected(expression: str, exc: type[Exception]) -> None:
    with pytest.raises(exc):
        calc(expression)


def test_malicious_case_count_meets_threshold() -> None:
    assert len(_MALICIOUS_CASES) >= 50


# ---------------------------------------------------------------------------
# DoS defenses
# ---------------------------------------------------------------------------


def test_node_limit_exceeded_rejects() -> None:
    expr = "1" + "+1" * 200
    with pytest.raises(ExpressionTooComplexError):
        calc(expr)


def test_expression_length_limit_rejects() -> None:
    expr = "1" + "+1" * 2000
    assert len(expr) > 3000
    with pytest.raises(ExpressionTooComplexError):
        calc(expr)


def test_node_limit_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOOTOOL_CALC_MAX_NODES", "9999")
    expr   = "1" + "+1" * 200
    result = calc(expr)
    assert Decimal(result["result"]) == Decimal(201)


def test_expr_len_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOOTOOL_CALC_MAX_EXPR_LEN", "10")
    with pytest.raises(ExpressionTooComplexError):
        calc("1+2+3+4+5+6+7+8")


# ---------------------------------------------------------------------------
# variable substitution
# ---------------------------------------------------------------------------


def test_variable_substitution_integer() -> None:
    result = calc("x*2+y", {"x": "3", "y": "5"})
    assert result["result"] == "11"


def test_variable_substitution_decimal_precision() -> None:
    result = calc("x+y", {"x": "0.1", "y": "0.2"})
    assert result["result"] == "0.3"


def test_undefined_variable_raises() -> None:
    with pytest.raises(UndefinedVariableError) as info:
        calc("a+b", {"a": "1"})
    assert info.value.name == "b"


def test_variable_must_be_decimal_string() -> None:
    with pytest.raises(DomainConstraintError):
        calc("x+1", {"x": "not-a-number"})


def test_variable_requires_string_values() -> None:
    with pytest.raises(DomainConstraintError):
        calc("x+1", {"x": 1})  # type: ignore[dict-item]


def test_constants_pi_e_tau() -> None:
    pi  = calc("pi")["result"]
    e   = calc("e")["result"]
    tau = calc("tau")["result"]
    assert Decimal(pi).quantize(Decimal("0.0000001"))  == Decimal("3.1415927")
    assert Decimal(e).quantize(Decimal("0.0000001"))   == Decimal("2.7182818")
    assert Decimal(tau).quantize(Decimal("0.0000001")) == Decimal("6.2831853")


# ---------------------------------------------------------------------------
# numeric correctness
# ---------------------------------------------------------------------------


def test_integer_arithmetic() -> None:
    assert calc("1+2*3")["result"]   == "7"
    assert calc("(1+2)*3")["result"] == "9"
    assert calc("10-4-3")["result"]  == "3"
    assert calc("100/4")["result"]   == "25"


def test_integer_power() -> None:
    assert calc("2**10")["result"]   == "1024"
    assert calc("3**0")["result"]    == "1"
    assert calc("(-2)**3")["result"] == "-8"


def test_modulo_and_floordiv() -> None:
    assert calc("10 % 3")["result"]  == "1"
    assert calc("10 // 3")["result"] == "3"


def test_unary_negative_positive() -> None:
    assert calc("-5")["result"]    == "-5"
    assert calc("+5")["result"]    == "5"
    assert calc("-(-5)")["result"] == "5"


def test_division_by_zero_domain_error() -> None:
    with pytest.raises(DomainConstraintError):
        calc("1/0")
    with pytest.raises(DomainConstraintError):
        calc("1 % 0")
    with pytest.raises(DomainConstraintError):
        calc("1 // 0")


def test_sqrt_and_transcendentals() -> None:
    result = calc("sqrt(2)")
    assert result["result"].startswith("1.4142135623730950")

    cos_result = calc("cos(0)")
    assert Decimal(cos_result["result"]).quantize(Decimal("0.0000000001")) == Decimal("1.0000000000")

    sin_pi = calc("sin(pi)")
    assert abs(Decimal(sin_pi["result"])) < Decimal("1e-40")

    exp_one = calc("exp(1)")
    assert Decimal(exp_one["result"]).quantize(Decimal("0.0000000001")) == Decimal("2.7182818285")


def test_log_variants() -> None:
    assert Decimal(calc("log10(1000)")["result"]).quantize(Decimal("0.000001")) == Decimal("3.000000")
    assert Decimal(calc("log2(8)")["result"]).quantize(Decimal("0.000001"))     == Decimal("3.000000")
    assert Decimal(calc("ln(e)")["result"]).quantize(Decimal("0.000001"))       == Decimal("1.000000")


def test_log_domain_error() -> None:
    with pytest.raises(DomainConstraintError):
        calc("log(0)")
    with pytest.raises(DomainConstraintError):
        calc("ln(-1)")


def test_asin_acos_domain() -> None:
    with pytest.raises(DomainConstraintError):
        calc("asin(2)")
    with pytest.raises(DomainConstraintError):
        calc("acos(-2)")


def test_sqrt_negative() -> None:
    with pytest.raises(DomainConstraintError):
        calc("sqrt(-1)")


def test_noninteger_pow_goes_through_mpmath() -> None:
    result = calc("2**(1/2)")
    assert Decimal(result["result"]).quantize(Decimal("0.0000000001")) == Decimal("1.4142135624")


def test_abs_floor_ceil_round() -> None:
    assert calc("abs(-7)")["result"]         == "7"
    assert calc("floor(2.7)")["result"]      == "2"
    assert calc("ceil(2.1)")["result"]       == "3"
    assert calc("round(2.5)")["result"]      == "2"
    assert calc("round(3.5)")["result"]      == "4"
    assert calc("round(2.345, 2)")["result"] == "2.34"


def test_pow_function() -> None:
    assert calc("pow(2, 10)")["result"] == "1024"


def test_atan2() -> None:
    result = calc("atan2(1, 1)")
    assert Decimal(result["result"]).quantize(Decimal("0.000001")) == Decimal("0.785398")


def test_precision_argument() -> None:
    low  = calc("sqrt(2)", precision=10)["result"]
    high = calc("sqrt(2)", precision=50)["result"]
    assert len(high) > len(low)


# ---------------------------------------------------------------------------
# trace structure
# ---------------------------------------------------------------------------


def test_trace_basic_structure() -> None:
    result = calc("1+2", trace_level="full")
    trace  = result["trace"]
    assert trace["tool"]    == "core.calc"
    assert trace["formula"] == "1+2"
    assert trace["output"]  == "3"
    assert trace["inputs"]["expression"] == "1+2"
    assert trace["inputs"]["precision"]  == 50
    assert isinstance(trace["parsed_ast_summary"], dict)
    assert trace["parsed_ast_summary"]["BinOp"] == 1


def test_trace_summary_level_omits_steps() -> None:
    result = calc("1+2+3", trace_level="summary")
    assert result["trace"]["steps"] == []


def test_trace_full_records_steps() -> None:
    result = calc("1+2*3", trace_level="full")
    steps  = result["trace"]["steps"]
    assert len(steps) >= 2
    labels = [s["label"] for s in steps]
    assert "*" in labels
    assert "+" in labels


# ---------------------------------------------------------------------------
# REGISTRY integration
# ---------------------------------------------------------------------------


def test_core_calc_registered_in_registry() -> None:
    from sootool.core.registry import REGISTRY
    from sootool.server import _register_core_tools
    _register_core_tools()
    names = set(REGISTRY._tools.keys())  # type: ignore[attr-defined]
    assert "core.calc" in names


def test_core_calc_via_invoke_tool() -> None:
    from sootool.server import invoke_tool
    result = invoke_tool("core.calc", {
        "expression": "x*2+y",
        "variables":  {"x": "3", "y": "5"},
    })
    assert result["result"]        == "11"
    assert result["trace"]["tool"] == "core.calc"


def test_core_calc_via_invoke_tool_full_trace() -> None:
    from sootool.server import invoke_tool
    result = invoke_tool("core.calc", {
        "expression":  "2**10",
        "trace_level": "full",
    })
    assert result["result"] == "1024"
    assert result["trace"]["steps"], "full trace must include evaluation steps"


# ---------------------------------------------------------------------------
# misc
# ---------------------------------------------------------------------------


def test_precision_invalid() -> None:
    with pytest.raises(DomainConstraintError):
        calc("1+1", precision=0)


def test_expression_not_string() -> None:
    with pytest.raises(InvalidExpressionError):
        calc(123)  # type: ignore[arg-type]


def test_large_integer_precision_preserved() -> None:
    result = calc("2**64")
    assert result["result"] == "18446744073709551616"


def test_nested_parentheses_within_limit() -> None:
    expr = "(" * 30 + "1+1" + ")" * 30
    assert calc(expr)["result"] == "2"
