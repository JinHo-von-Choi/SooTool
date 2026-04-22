"""Tests for tax.kr_withholding_simple tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors   import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies      import UnsupportedPolicyError


def call_withholding(**kwargs):
    return REGISTRY.invoke("tax.kr_withholding_simple", **kwargs)


class TestKrWithholding:
    def test_withholding_single_dependent_3M(self):
        """월급여 3,000,000원, 부양가족 1명 → 비음수 원천징수세액."""
        result = call_withholding(
            monthly_salary="3000000",
            dependents=1,
            year=2026,
        )
        tax = int(result["withheld_tax"])
        assert tax >= 0, "원천징수세액은 0 이상이어야 합니다."

    def test_withholding_more_dependents_lower_tax(self):
        """부양가족 증가 → 원천징수세액 감소 (또는 동일)."""
        r1 = call_withholding(monthly_salary="5000000", dependents=1, year=2026)
        r4 = call_withholding(monthly_salary="5000000", dependents=4, year=2026)
        assert int(r1["withheld_tax"]) >= int(r4["withheld_tax"])

    def test_withholding_high_salary_positive_tax(self):
        """월급여 10,000,000원 → 양의 원천징수세액."""
        result = call_withholding(
            monthly_salary="10000000",
            dependents=1,
            year=2026,
        )
        assert int(result["withheld_tax"]) > 0

    def test_withholding_very_low_salary_near_zero_tax(self):
        """최저임금 수준 월급여 + 부양가족 다수 → 원천징수세액 0 또는 매우 낮음."""
        result = call_withholding(
            monthly_salary="1000000",
            dependents=4,
            year=2026,
        )
        assert int(result["withheld_tax"]) == 0

    def test_withholding_returns_policy_version(self):
        result = call_withholding(
            monthly_salary="5000000",
            dependents=1,
            year=2026,
        )
        assert "policy_version" in result
        pv = result["policy_version"]
        assert pv["year"] == 2026

    def test_withholding_invalid_negative_salary(self):
        with pytest.raises(InvalidInputError):
            call_withholding(monthly_salary="-1", dependents=1, year=2026)

    def test_withholding_invalid_zero_dependents(self):
        with pytest.raises(InvalidInputError):
            call_withholding(monthly_salary="3000000", dependents=0, year=2026)

    def test_withholding_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call_withholding(monthly_salary="3000000", dependents=1, year=2099)

    def test_withholding_result_is_integer_won(self):
        """원천징수세액은 원 단위 정수여야 한다 (DOWN 반올림)."""
        result = call_withholding(
            monthly_salary="5000000",
            dependents=1,
            year=2026,
        )
        tax_str = result["withheld_tax"]
        assert "." not in tax_str or tax_str.endswith(".0") or Decimal(tax_str) % 1 == 0
