"""``sootool.sdk`` 라이브러리 인터페이스 시험.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from sootool import sdk
from sootool.core.errors import InvalidInputError, SooToolError
from sootool.core.registry import REGISTRY
from sootool.runtime import NAMESPACE_MODULES

_ROOT = Path(__file__).resolve().parents[1]


def test_every_namespace_is_exposed():
    assert sdk.namespaces() == sorted(NAMESPACE_MODULES)
    for name in NAMESPACE_MODULES:
        assert isinstance(getattr(sdk, name), sdk.Namespace)


def test_call_returns_the_same_structure_as_the_registry():
    via_sdk = sdk.tax.kr_income(taxable_income="50000000", year=2026)
    direct  = REGISTRY.invoke("tax.kr_income", taxable_income="50000000", year=2026)
    assert via_sdk["tax"] == direct["tax"] == "6240000"
    assert via_sdk["_meta"]["integrity"]["input_hash"] == direct["_meta"]["integrity"]["input_hash"]


def test_positional_and_keyword_arguments_both_work():
    assert sdk.core.add(["1", "2"])["result"] == "3"
    assert sdk.core.sub("5", b="3")["result"] == "2"


def test_numbers_are_accepted_for_string_parameters_but_not_for_typed_ones():
    out = sdk.tax.kr_income(taxable_income=50_000_000, year=2026)
    assert out["tax"] == "6240000"
    assert "input_coerced" not in out["_meta"]


def test_floats_are_converted_and_reported():
    out = sdk.core.add(operands=[0.1, 2, "3"])
    assert out["result"] == "5.1"
    assert out["_meta"]["input_coerced"] == [{"argument": "operands", "from": "float", "as": "0.1"}]


def test_nested_tool_arguments_are_not_coerced():
    out = sdk.core.batch(items=[{"id": "a", "tool": "tax.kr_income", "args": {"taxable_income": "50000000", "year": 2026}}])
    assert out["results"][0]["status"] == "ok"


def test_policy_arguments_are_available():
    out = sdk.tax.kr_income(taxable_income="50000000", year=2026, as_of="2026-06-01")
    assert out["policy_effective_date"] == "2026-01-01"


def test_errors_are_raised_as_typed_exceptions():
    with pytest.raises(SooToolError):
        sdk.core.div("1", "0")
    with pytest.raises(InvalidInputError):
        sdk.core.add(operands=["abc"])


def test_unknown_names_list_the_available_ones():
    with pytest.raises(AttributeError, match="kr_income"):
        sdk.tax.no_such_tool  # noqa: B018
    with pytest.raises(AttributeError, match="payroll"):
        sdk.no_such_namespace  # noqa: B018


def test_tool_objects_carry_signature_and_description():
    import inspect

    tool = sdk.tax.kr_income
    assert "taxable_income" in inspect.signature(tool).parameters
    assert "year" in inspect.signature(tool).parameters
    assert tool.__doc__ and len(tool.__doc__) > 60
    assert tool.full_name == "tax.kr_income"


def test_importing_a_namespace_does_not_import_the_mcp_package():
    code = textwrap.dedent(
        """
        import sys
        from sootool.sdk import tax
        tax.kr_income(taxable_income="1000000", year=2026)
        raise SystemExit(1 if any(m == "mcp" or m.startswith("mcp.") for m in sys.modules) else 0)
        """
    )
    assert subprocess.run([sys.executable, "-c", code], check=False, cwd=_ROOT).returncode == 0  # noqa: S603


def test_generated_type_declarations_are_current():
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(_ROOT / "scripts" / "gen_sdk_stubs.py"), "--check"],
        check=False, capture_output=True, text=True, cwd=_ROOT,
    )
    assert result.returncode == 0, result.stdout


def test_type_checker_sees_precise_results_and_rejects_wrong_arguments(tmp_path):
    mypy_api = pytest.importorskip("mypy.api")
    probe = tmp_path / "probe.py"
    probe.write_text(textwrap.dedent(
        """
        from sootool.sdk import tax

        out = tax.kr_income(taxable_income=50_000_000, year=2026)
        reveal_type(out["tax"])
        tax.kr_income(taxable_income=1, year="2026")
        """
    ))
    stdout, _, _ = mypy_api.run(["--config-file", str(_ROOT / "pyproject.toml"), str(probe)])
    assert 'Revealed type is "builtins.str"' in stdout or 'Revealed type is "str"' in stdout
    assert 'Argument "year"' in stdout
