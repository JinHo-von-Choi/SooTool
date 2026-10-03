"""Tests for tax.kr_corporate.

기대값은 법인세법 제55조제1항 표(누적 세액 상수 포함)와 조세특례제한법 제132조제1항 세율로
직접 계산한 값이다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_corporate", **kwargs)


class TestKrCorporate:
    def test_2억_boundary_10pct(self):
        """과세표준 2억원: 과세표준의 100분의 10 = 20,000,000"""
        r = call(taxable_income="200000000", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("20000000")

    def test_500억_spans_3_brackets(self):
        """500억원: 39억8천만원 + (300억 x 22%) = 3,980,000,000 + 6,600,000,000"""
        r = call(taxable_income="50000000000", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("10580000000")

    def test_4000억_top_bracket(self):
        """4,000억원: 655억8천만원 + (1,000억 x 25%) = 65,580,000,000 + 25,000,000,000"""
        r = call(taxable_income="400000000000", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("90580000000")

    def test_zero_income(self):
        r = call(taxable_income="0", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("0")

    def test_small_firm_minimum_tax_floor(self):
        """감면이 없으면 최저한세가 작동하지 않는다: 1억 x 10% = 1,000만."""
        r = call(taxable_income="100000000", year=2026, is_small=True)
        assert Decimal(r["base_tax"]) == Decimal("10000000")
        assert Decimal(r["minimum_tax"]) == Decimal("7000000")
        assert Decimal(r["tax"]) == Decimal("10000000")

    def test_general_firm_without_reductions_keeps_base_tax(self):
        """일반법인 150억, 감면 없음: 2천만 + 148억 x 20% = 2,980,000,000 그대로."""
        r = call(taxable_income="15000000000", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("2980000000")
        assert Decimal(r["tax"]) == Decimal("2980000000")
        assert Decimal(r["minimum_tax_adjustment"]) == Decimal("0")

    def test_negative_income_raises(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="-1", year=2026)

    def test_unsupported_year_raises(self):
        with pytest.raises(UnsupportedPolicyError):
            call(taxable_income="100000000", year=2099)

    def test_policy_version_exposed(self):
        r = call(taxable_income="100000000", year=2026)
        pv = r["policy_version"]
        assert pv["year"] == 2026
        assert "sha256" in pv

    def test_trace_present(self):
        r = call(taxable_income="100000000", year=2026)
        assert "trace" in r
        assert r["trace"]["tool"] == "tax.kr_corporate"


class TestKrCorporate2025:
    def test_2025_rates(self):
        """2025-01-01 시행본: 2억 x 9% = 18,000,000."""
        r = call(taxable_income="200000000", year=2025)
        assert Decimal(r["base_tax"]) == Decimal("18000000")

    def test_2025_500억(self):
        """2025 시행본 500억: 37억8천만원 + (300억 x 21%) = 10,080,000,000."""
        r = call(taxable_income="50000000000", year=2025)
        assert Decimal(r["base_tax"]) == Decimal("10080000000")


class TestKrCorporateSmallRental:
    def test_small_rental_corp_1억(self):
        """제55조제1항제2호: 200억 이하 과세표준의 100분의 20. 1억 x 20% = 20,000,000."""
        r = call(taxable_income="100000000", year=2026, is_small_rental_corp=True)
        assert Decimal(r["base_tax"]) == Decimal("20000000")

    def test_small_rental_corp_300억(self):
        """300억: 40억원 + (100억 x 22%) = 6,200,000,000."""
        r = call(taxable_income="30000000000", year=2026, is_small_rental_corp=True)
        assert Decimal(r["base_tax"]) == Decimal("6200000000")

    def test_small_rental_corp_2025(self):
        """2025 시행본 제2호: 1억 x 19% = 19,000,000."""
        r = call(taxable_income="100000000", year=2025, is_small_rental_corp=True)
        assert Decimal(r["base_tax"]) == Decimal("19000000")


class TestKrCorporateMinimumTax:
    """과세표준 10억: 산출세액 = 2천만 + 8억 x 20% = 180,000,000."""

    def test_reductions_above_minimum_tax_allowed(self):
        """중소기업 감면 8천만: 감면 후 1억 >= 최저한세 10억 x 7% = 7천만 → 1억."""
        r = call(taxable_income="1000000000", year=2026, is_small=True, reductions="80000000")
        assert Decimal(r["base_tax"]) == Decimal("180000000")
        assert Decimal(r["minimum_tax"]) == Decimal("70000000")
        assert Decimal(r["tax"]) == Decimal("100000000")
        assert Decimal(r["minimum_tax_adjustment"]) == Decimal("0")

    def test_reductions_limited_by_small_minimum_tax(self):
        """중소기업 감면 1.5억: 감면 후 3천만 < 7천만 → 7천만, 감면 배제 4천만."""
        r = call(taxable_income="1000000000", year=2026, is_small=True, reductions="150000000")
        assert Decimal(r["tax"]) == Decimal("70000000")
        assert Decimal(r["minimum_tax_adjustment"]) == Decimal("40000000")

    def test_reductions_limited_by_general_minimum_tax(self):
        """일반법인 감면 1.5억: 최저한세 10억 x 10% = 1억 → 1억."""
        r = call(taxable_income="1000000000", year=2026, reductions="150000000")
        assert Decimal(r["minimum_tax"]) == Decimal("100000000")
        assert Decimal(r["tax"]) == Decimal("100000000")

    def test_general_minimum_tax_brackets(self):
        """일반법인 2,000억 최저한세: 100억 x 10% + 900억 x 12% + 1,000억 x 17% = 288억."""
        r = call(taxable_income="200000000000", year=2026)
        assert Decimal(r["minimum_tax"]) == Decimal("28800000000")

    def test_sme_graduation_first_3y(self):
        """중소기업 졸업 후 3년 이내 8%: 10억 x 8% = 8천만."""
        r = call(
            taxable_income="1000000000", year=2026,
            sme_graduation_period="first_3y", reductions="150000000",
        )
        assert Decimal(r["minimum_tax"]) == Decimal("80000000")
        assert Decimal(r["tax"]) == Decimal("80000000")

    def test_sme_graduation_next_2y(self):
        """그다음 2년 이내 9%: 10억 x 9% = 9천만."""
        r = call(
            taxable_income="1000000000", year=2026,
            sme_graduation_period="next_2y", reductions="150000000",
        )
        assert Decimal(r["tax"]) == Decimal("90000000")

    def test_pre_deduction_income_base(self):
        """손금산입 전 과세표준 30억 x 7% = 2.1억 > 산출세액 1.8억 → 2.1억."""
        r = call(
            taxable_income="1000000000", year=2026, is_small=True,
            pre_deduction_income="3000000000",
        )
        assert Decimal(r["minimum_tax"]) == Decimal("210000000")
        assert Decimal(r["tax"]) == Decimal("210000000")
        assert Decimal(r["minimum_tax_adjustment"]) == Decimal("30000000")

    def test_pre_deduction_below_income_raises(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="1000000000", year=2026, pre_deduction_income="1")

    def test_graduation_with_small_raises(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="1000000000", year=2026, is_small=True, sme_graduation_period="first_3y")

    def test_invalid_graduation_raises(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="1000000000", year=2026, sme_graduation_period="forever")

    def test_negative_reductions_raises(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="1000000000", year=2026, reductions="-1")
