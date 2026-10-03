from __future__ import annotations

import math
import re
from decimal import Decimal
from pathlib import Path

import pytest

from sootool.core import limits
from sootool.core.errors import DomainConstraintError, InputLimitError
from sootool.core.registry import REGISTRY


def _load_all() -> None:
    from sootool import server
    server._load_modules()


# --- limits 모듈 단위 ---

def test_limit_returns_default_without_env(monkeypatch):
    monkeypatch.delenv("SOOTOOL_LIMIT_LOAN_MONTHS", raising=False)
    assert limits.limit("LOAN_MONTHS") == 1_200


def test_limit_env_override(monkeypatch):
    monkeypatch.setenv("SOOTOOL_LIMIT_LOAN_MONTHS", "60")
    assert limits.limit("LOAN_MONTHS") == 60


@pytest.mark.parametrize("raw", ["abc", "0", "-5", " "])
def test_limit_invalid_env_falls_back_to_default(monkeypatch, raw):
    monkeypatch.setenv("SOOTOOL_LIMIT_LOAN_MONTHS", raw)
    assert limits.limit("LOAN_MONTHS") == 1_200


def test_limit_unknown_name_raises():
    with pytest.raises(KeyError):
        limits.limit("NO_SUCH_LIMIT")


def test_ensure_max_accepts_boundary(monkeypatch):
    monkeypatch.setenv("SOOTOOL_LIMIT_LOAN_MONTHS", "10")
    limits.ensure_max("LOAN_MONTHS", 10)
    limits.ensure_max("LOAN_MONTHS", -10)


def test_ensure_max_rejects_over_limit_with_typed_error(monkeypatch):
    monkeypatch.setenv("SOOTOOL_LIMIT_LOAN_MONTHS", "10")
    with pytest.raises(InputLimitError) as info:
        limits.ensure_max("LOAN_MONTHS", 11, "months")
    assert info.value.field == "months"
    assert info.value.limit == 10
    assert info.value.observed == 11
    assert isinstance(info.value, DomainConstraintError)


def test_ensure_max_uses_absolute_value(monkeypatch):
    monkeypatch.setenv("SOOTOOL_LIMIT_LOAN_MONTHS", "10")
    with pytest.raises(InputLimitError):
        limits.ensure_max("LOAN_MONTHS", -11)


# --- 구조 검사: 선언된 한도는 모두 실제 도구에서 사용된다 ---

def test_every_declared_limit_is_enforced_in_source():
    src_root = Path(limits.__file__).resolve().parents[1]
    corpus   = "\n".join(
        p.read_text(encoding="utf-8")
        for p in src_root.rglob("*.py")
    )
    for name in limits._DEFAULTS:
        assert re.search(rf'(ensure_max|limit)\(\s*"{name}"', corpus), f"미사용 한도: {name}"


# --- 도구별 한도 초과는 계산 전에 타입 오류로 거부된다 ---

_OVER_LIMIT_CASES = [
    ("probability.factorial",         {"n": 10**6}),
    ("probability.nCr",               {"n": 10**9, "r": 5 * 10**8}),
    ("probability.nPr",               {"n": 10**6, "r": 10**6}),
    ("crypto.is_prime",               {"n": "97", "k": 10**6}),
    ("finance.loan_schedule",         {"principal": "1000000", "annual_rate": "0.05", "months": 10**6}),
    ("finance.irr",                   {"cashflows": ["-100", "10", "120"], "max_iter": 10**9}),
    ("math.integrate_simpson",        {"expression": "x", "a": "0", "b": "1", "n": 10**8}),
    ("math.integrate_gauss_legendre", {"expression": "x", "a": "0", "b": "1", "degree": 10**5}),
    ("datetime.add_business_days",    {"start_date": "2026-01-01", "days": 10**7}),
    ("core.calc",                     {"expression": "sqrt(2)", "precision": 10**6}),
    ("stats.bootstrap_ci",            {"values": ["1", "2", "3"], "n_resamples": 10**8}),
    ("geometry.matrix_inverse",      {"M": [["1"] * 201] * 201}),
    ("geometry.matrix_multiply",     {"A": [["1"] * 201], "B": [["1"]] * 201}),
    ("math.polynomial_roots",        {"coefficients": ["1"] * 258}),
    ("math.fft",                     {"samples": ["1"] * 65_537}),
    ("crypto.gcd",                   {"a": "9" * 2_049, "b": "3"}),
    ("crypto.is_prime",              {"n": "9" * 2_049}),
    ("crypto.modpow",                {"base": "2", "exponent": "9" * 2_049, "modulus": "7"}),
    ("datetime.count_business_days", {"start": "1900-01-01", "end": "2900-01-01"}),
    ("pm.monte_carlo_schedule",       {
        "tasks": [{"id": "a", "optimistic": "1", "most_likely": "2", "pessimistic": "3"}],
        "n": 10**8,
    }),
]


@pytest.mark.parametrize(("tool", "kwargs"), _OVER_LIMIT_CASES, ids=[c[0] for c in _OVER_LIMIT_CASES])
def test_over_limit_input_is_rejected_with_typed_error(tool, kwargs):
    _load_all()
    with pytest.raises(InputLimitError):
        REGISTRY.invoke(tool, **kwargs)


# --- 대형 정수 직렬화: 4300자리 변환 한계에 걸리지 않는다 ---

def test_factorial_beyond_int_str_digit_limit():
    _load_all()
    out = REGISTRY.invoke("probability.factorial", n=2000)
    assert len(out["result"]) > 4300
    assert Decimal(out["result"]) == Decimal(math.factorial(2000))


def test_ncr_beyond_int_str_digit_limit():
    _load_all()
    out = REGISTRY.invoke("probability.nCr", n=20000, r=10000)
    assert len(out["result"]) > 4300
    assert Decimal(out["result"]) == Decimal(math.comb(20000, 10000))


def test_env_override_tightens_limit(monkeypatch):
    _load_all()
    monkeypatch.setenv("SOOTOOL_LIMIT_COMBINATORICS_N", "10")
    with pytest.raises(InputLimitError):
        REGISTRY.invoke("probability.factorial", n=11)
    assert REGISTRY.invoke("probability.factorial", n=10)["result"] == "3628800"


# --- 인자 전체 크기 검사 (모든 호출 경로 공통) ---

def test_oversized_string_argument_is_rejected_before_any_tool_runs():
    _load_all()
    with pytest.raises(InputLimitError) as info:
        REGISTRY.invoke("core.calc", expression="1+" * 60_000 + "1")
    assert info.value.field == "expression"


def test_oversized_list_argument_is_rejected():
    _load_all()
    with pytest.raises(InputLimitError) as info:
        REGISTRY.invoke("core.add", operands=["1"] * 100_001)
    assert info.value.field == "operands[]" or info.value.field == "operands"


def test_deeply_nested_argument_is_rejected():
    _load_all()
    nested: object = "1"
    for _ in range(20):
        nested = [nested]
    with pytest.raises(InputLimitError):
        REGISTRY.invoke("core.add", operands=nested)


def test_total_node_budget_is_enforced(monkeypatch):
    _load_all()
    monkeypatch.setenv("SOOTOOL_LIMIT_ARG_NODES", "50")
    with pytest.raises(InputLimitError) as info:
        REGISTRY.invoke("core.add", operands=["1"] * 60)
    assert info.value.field == "arguments"


def test_arguments_nested_inside_batch_items_are_checked_with_the_outer_call():
    _load_all()
    with pytest.raises(InputLimitError) as info:
        REGISTRY.invoke(
            "core.batch",
            items=[{"id": "big", "tool": "core.add", "args": {"operands": ["1"] * 100_001}}],
        )
    assert info.value.field == "items[].args.operands"


def test_arguments_at_the_limit_are_accepted():
    _load_all()
    out = REGISTRY.invoke("core.add", operands=["1"] * 100_000)
    assert out["result"] == "100000"


def test_environment_override_widens_the_argument_limit(monkeypatch):
    _load_all()
    monkeypatch.setenv("SOOTOOL_LIMIT_ARG_LIST_ITEMS", "100002")
    assert REGISTRY.invoke("core.add", operands=["1"] * 100_001)["result"] == "100001"


# --- 한도 경계에서의 최악 실행 시간 ---

_WORST_CASE_BUDGET_S = 15.0

_AT_LIMIT_CASES = [
    ("geometry.matrix_inverse",       lambda: {"M": [[str((i * j) % 7 + (10 if i == j else 0)) for j in range(200)] for i in range(200)]}),
    ("geometry.matrix_multiply",      lambda: {"A": [["1.5"] * 200] * 200, "B": [["2.5"] * 200] * 200}),
    ("math.polynomial_roots",         lambda: {"coefficients": [str(i + 1) for i in range(257)]}),
    ("math.fft",                      lambda: {"samples": ["1.5"] * 65_536}),
    ("crypto.is_prime",               lambda: {"n": "9" * 2_047 + "1", "k": 20}),
    ("crypto.modpow",                 lambda: {"base": "3", "exponent": "7" * 2_048, "modulus": "9" * 2_047 + "1"}),
    ("math.interpolate_cubic_spline", lambda: {"xs": [str(i) for i in range(100_000)], "ys": ["1"] * 100_000, "x_query": "5"}),
    ("datetime.count_business_days",  lambda: {"start": "1900-01-01", "end": "2173-10-15"}),
    ("probability.factorial",         lambda: {"n": 20_000}),
    ("math.integrate_simpson",        lambda: {"expression": "sin(x)*x", "a": "0", "b": "3", "n": 20_000}),
]


@pytest.mark.parametrize(("tool", "make_kwargs"), _AT_LIMIT_CASES, ids=[c[0] for c in _AT_LIMIT_CASES])
def test_worst_case_input_completes_within_the_time_budget(tool, make_kwargs):
    """한도 경계의 입력이 한 번의 호출에서 시간 예산 안에 끝난다(입력 한도가 실행 시간을 묶는다)."""
    import time

    _load_all()
    started = time.monotonic()
    REGISTRY.invoke(tool, **make_kwargs())
    assert time.monotonic() - started < _WORST_CASE_BUDGET_S
