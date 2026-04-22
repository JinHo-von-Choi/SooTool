"""Tests for tax.kr_income tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call_kr_income(**kwargs):
    return REGISTRY.invoke("tax.kr_income", **kwargs)


class TestKrIncome:
    def test_kr_income_5000만원_2026(self):
        """50,000,000원 과세표준에 2026년 기준 세율 적용.

        계산 근거:
          0 ~ 14,000,000: 14,000,000 * 6% = 840,000
          14,000,001 ~ 50,000,000: 36,000,000 * 15% = 5,400,000
          합계 = 6,240,000
        """
        result = call_kr_income(taxable_income="50000000", year=2026)
        assert result["tax"] == "6240000"
        assert result["marginal_rate"] == "0.15"
        assert "policy_version" in result
        assert result["policy_version"]["year"] == 2026

    def test_kr_income_14M_boundary(self):
        """14,000,000은 첫 번째 구간 상한(이하 포함) → 6%만 적용."""
        result = call_kr_income(taxable_income="14000000", year=2026)
        assert result["tax"] == "840000"
        assert result["marginal_rate"] == "0.06"

    def test_kr_income_88M(self):
        """88,000,000원: 세 번째 구간(24%)까지 적용."""
        result = call_kr_income(taxable_income="88000000", year=2026)
        # 14M*6% + 36M*15% + 38M*24%
        # = 840_000 + 5_400_000 + 9_120_000 = 15_360_000
        assert result["tax"] == "15360000"

    def test_kr_income_zero(self):
        result = call_kr_income(taxable_income="0", year=2026)
        assert result["tax"] == "0"

    def test_kr_income_returns_breakdown(self):
        result = call_kr_income(taxable_income="30000000", year=2026)
        assert "breakdown" in result
        assert len(result["breakdown"]) > 0

    def test_kr_income_effective_rate_positive(self):
        result = call_kr_income(taxable_income="50000000", year=2026)
        eff = Decimal(result["effective_rate"])
        assert eff > Decimal("0")
        assert eff < Decimal("1")

    def test_kr_income_year_2099_unsupported(self):
        """존재하지 않는 연도는 UnsupportedPolicyError를 발생시켜야 한다."""
        with pytest.raises(UnsupportedPolicyError):
            call_kr_income(taxable_income="50000000", year=2099)

    def test_kr_income_policy_version_fields(self):
        result = call_kr_income(taxable_income="50000000", year=2026)
        pv = result["policy_version"]
        assert "year" in pv
        assert "sha256" in pv
        assert "effective_date" in pv
        assert "notice_no" in pv

    def test_kr_income_high_income_top_bracket(self):
        """1,100,000,000원 → 최고 구간 45% 적용."""
        result = call_kr_income(taxable_income="1100000000", year=2026)
        assert result["marginal_rate"] == "0.45"
        assert int(result["tax"]) > 0
