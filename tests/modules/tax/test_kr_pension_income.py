"""Tests for tax.kr_pension_income (사적연금 원천징수, 분리과세 판정, 연금소득공제).

기대값은 소득세법 제129조제1항제5호의2·제5호의3·제6호나목(2025-01-01 시행본과 2026-07-01 시행본),
제14조제3항제9호다목, 제47조의2, 제64조의4, 지방세법 제103조의13제1항을 조문대로 계산하고
원 미만을 버린 값이다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_pension_income", **kwargs)


class TestPrivatePensionRates:
    @pytest.mark.parametrize(("age", "rate", "tax"), [
        (69, "0.05", "50000"),   # 70세 미만 100분의 5
        (70, "0.04", "40000"),   # 70세 이상 80세 미만 100분의 4
        (79, "0.04", "40000"),
        (80, "0.03", "30000"),   # 80세 이상 100분의 3
    ])
    def test_age_boundaries(self, age, rate, tax):
        r = call(year=2026, private_pension_amount="1000000", age=age)
        assert Decimal(r["private_pension_rate"]) == Decimal(rate)
        assert Decimal(r["private_pension_tax"]) == Decimal(tax)

    def test_local_income_tax_ten_percent(self):
        """100만원, 65세: 소득세 50,000, 지방소득세 5,000, 합계 55,000 (5.5%)."""
        r = call(year=2026, private_pension_amount="1000000", age=65)
        assert Decimal(r["withholding_income_tax"]) == Decimal("50000")
        assert Decimal(r["withholding_local_tax"]) == Decimal("5000")
        assert Decimal(r["withholding_total"]) == Decimal("55000")

    def test_lifetime_annuity_2026_three_percent(self):
        """2026 종신계약 100분의 3, 65세 나이 세율 5%보다 낮으므로 3% 적용."""
        r = call(year=2026, private_pension_amount="1000000", age=65, lifetime_annuity=True)
        assert Decimal(r["private_pension_rate"]) == Decimal("0.03")
        assert Decimal(r["private_pension_tax"]) == Decimal("30000")

    def test_lifetime_annuity_2025_four_percent(self):
        """2025 지급분 종신계약 100분의 4 (법률 제21221호 시행 전)."""
        r = call(year=2025, private_pension_amount="1000000", age=65, lifetime_annuity=True)
        assert Decimal(r["private_pension_rate"]) == Decimal("0.04")

    def test_lifetime_and_age_take_lower_rate_2025(self):
        """2025 종신계약 4%와 80세 이상 3%가 겹치면 낮은 3%."""
        r = call(year=2025, private_pension_amount="1000000", age=85, lifetime_annuity=True)
        assert Decimal(r["private_pension_rate"]) == Decimal("0.03")

    def test_lifetime_without_age(self):
        r = call(year=2026, private_pension_amount="1000000", lifetime_annuity=True)
        assert Decimal(r["private_pension_tax"]) == Decimal("30000")

    def test_truncates_below_one_won(self):
        """333,333원 × 5% = 16,666.65 → 16,666, 지방소득세 1,666.6 → 1,666."""
        r = call(year=2026, private_pension_amount="333333", age=60)
        assert Decimal(r["private_pension_tax"]) == Decimal("16666")
        assert Decimal(r["withholding_local_tax"]) == Decimal("1666")

    def test_under_55_adds_note(self):
        r = call(year=2026, private_pension_amount="1000000", age=50)
        assert r["notes"]


class TestDeferredRetirement:
    @pytest.mark.parametrize(("years", "ratio", "tax"), [
        (10, "0.70", "210000"),  # 10년 이하 70%: 5,000,000 × 6% × 70%
        (11, "0.60", "180000"),  # 10년 초과 20년 이하 60%
        (20, "0.60", "180000"),
        (21, "0.50", "150000"),  # 20년 초과 50% (2026 지급분부터)
    ])
    def test_ratio_by_receipt_years_2026(self, years, ratio, tax):
        r = call(
            year=2026, deferred_retirement_amount="5000000",
            deferred_retirement_tax_rate="0.06", actual_receipt_years=years,
        )
        assert Decimal(r["deferred_retirement_ratio"]) == Decimal(ratio)
        assert Decimal(r["deferred_retirement_tax"]) == Decimal(tax)

    def test_2025_over_twenty_years_still_sixty_percent(self):
        """2025 지급분은 20년 초과 구간이 없어 10년 초과 전부 60%."""
        r = call(
            year=2025, deferred_retirement_amount="5000000",
            deferred_retirement_tax_rate="0.06", actual_receipt_years=21,
        )
        assert Decimal(r["deferred_retirement_ratio"]) == Decimal("0.60")
        assert Decimal(r["deferred_retirement_tax"]) == Decimal("180000")

    def test_deferred_excluded_from_threshold(self):
        """이연퇴직소득 연금수령분은 1,500만원 판정에서 빠진다 (제14조제3항제9호가목)."""
        r = call(
            year=2026, deferred_retirement_amount="30000000",
            deferred_retirement_tax_rate="0.06", actual_receipt_years=1,
        )
        assert r["separate_taxation_eligible"] is True
        assert Decimal(r["total_pension_amount"]) == Decimal("0")


class TestNonPensionWithdrawal:
    def test_fifteen_percent_plus_local(self):
        """연금외수령 200만원: 소득세 15% 300,000 + 지방소득세 30,000 = 330,000 (16.5%)."""
        r = call(year=2026, non_pension_withdrawal_amount="2000000")
        assert Decimal(r["non_pension_withdrawal_tax"]) == Decimal("300000")
        assert Decimal(r["withholding_local_tax"]) == Decimal("30000")
        assert Decimal(r["withholding_total"]) == Decimal("330000")


class TestSeparateTaxation:
    def test_exactly_threshold_is_separate(self):
        """연 1,500만원 이하이면 분리과세 (제14조제3항제9호다목)."""
        r = call(year=2026, private_pension_amount="15000000", age=65)
        assert r["separate_taxation_eligible"] is True
        assert Decimal(r["separate_taxation_option_tax"]) == Decimal("0")
        assert Decimal(r["total_pension_amount"]) == Decimal("0")

    def test_over_threshold_option_tax(self):
        """15,000,001원: 분리과세 아님, 15% 선택세액 2,250,000.15 → 2,250,000 (제64조의4제2호가목)."""
        r = call(year=2026, private_pension_amount="15000001", age=65)
        assert r["separate_taxation_eligible"] is False
        assert Decimal(r["separate_taxation_option_tax"]) == Decimal("2250000")
        assert r["notes"]

    def test_annual_total_overrides_payment_amount(self):
        r = call(
            year=2026, private_pension_amount="1000000", age=65,
            annual_private_pension_total="20000000",
        )
        assert r["separate_taxation_eligible"] is False
        assert Decimal(r["annual_private_pension_total"]) == Decimal("20000000")


class TestPensionIncomeDeduction:
    @pytest.mark.parametrize(("total", "deduction"), [
        ("3500000",  "3500000"),   # 350만원 이하 전액
        ("7000000",  "4900000"),   # 350만 + 350만 × 40%
        ("14000000", "6300000"),   # 490만 + 700만 × 20%
        ("41000000", "9000000"),   # 630만 + 2,700만 × 10% = 900만 (한도와 같음)
        ("50000000", "9000000"),   # 630만 + 3,600만 × 10% = 990만 → 한도 900만
    ])
    def test_brackets_and_cap(self, total, deduction):
        r = call(year=2026, public_pension_amount=total)
        assert Decimal(r["pension_income_deduction"]) == Decimal(deduction)
        assert Decimal(r["pension_income_amount"]) == Decimal(total) - Decimal(deduction)

    def test_private_over_threshold_joins_total_pension(self):
        """공적 1,000만 + 사적 2,000만(분리과세 아님) = 3,000만: 630만 + 1,600만 × 10% = 790만."""
        r = call(
            year=2026, public_pension_amount="10000000",
            private_pension_amount="20000000", age=65,
        )
        assert Decimal(r["total_pension_amount"]) == Decimal("30000000")
        assert Decimal(r["pension_income_deduction"]) == Decimal("7900000")

    def test_separate_private_excluded_from_total_pension(self):
        r = call(
            year=2026, public_pension_amount="10000000",
            private_pension_amount="12000000", age=65,
        )
        assert Decimal(r["total_pension_amount"]) == Decimal("10000000")
        assert Decimal(r["pension_income_deduction"]) == Decimal("5500000")


class TestAsOf:
    def test_2026_policy_not_in_effect_before_start(self):
        with pytest.raises(PolicyNotInEffectError):
            call(year=2026, private_pension_amount="1000000", age=65, as_of="2025-12-31")

    def test_2025_policy_on_last_day(self):
        r = call(year=2025, private_pension_amount="1000000", age=65, lifetime_annuity=True, as_of="2025-12-31")
        assert Decimal(r["private_pension_rate"]) == Decimal("0.04")


class TestErrors:
    def test_private_without_age(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, private_pension_amount="1000000")

    def test_deferred_without_rate(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, deferred_retirement_amount="1000000", actual_receipt_years=1)

    def test_deferred_rate_out_of_range(self):
        with pytest.raises(InvalidInputError):
            call(
                year=2026, deferred_retirement_amount="1000000",
                deferred_retirement_tax_rate="1.5", actual_receipt_years=1,
            )

    def test_receipt_years_zero(self):
        with pytest.raises(InvalidInputError):
            call(
                year=2026, deferred_retirement_amount="1000000",
                deferred_retirement_tax_rate="0.05", actual_receipt_years=0,
            )

    def test_negative_amount(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, non_pension_withdrawal_amount="-1")

    def test_age_out_of_range(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, private_pension_amount="1000000", age=200)
