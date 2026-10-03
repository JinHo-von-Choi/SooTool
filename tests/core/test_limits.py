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
        if p.name != "limits.py"
    )
    for name in limits._DEFAULTS:
        assert re.search(rf'ensure_max\(\s*"{name}"', corpus), f"미사용 한도: {name}"


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
