"""Tests for tax.kr_inheritance.

기대값은 상속세 및 증여세법 제18조~제21조·제24조 공제액, 제26조 세율표,
제69조제1항 신고세액공제율로 직접 계산한 값이다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_inheritance", **kwargs)


class TestKrInheritance:
    def test_5억_below_lump_sum(self):
        """5억 상속, 배우자 0 → 일괄공제 5억으로 taxable=0, tax=0."""
        r = call(gross_estate="500000000", spouse_inheritance="0", year=2026)
        assert Decimal(r["taxable_base"]) == Decimal("0")
        assert Decimal(r["tax"]) == Decimal("0")

    def test_10억_no_spouse(self):
        """10억 - 일괄공제 5억 = 과세표준 5억; 1억*10% + 4억*20% = 90M"""
        r = call(gross_estate="1000000000", spouse_inheritance="0", year=2026)
        assert Decimal(r["taxable_base"]) == Decimal("500000000")
        expected = Decimal("100000000") * Decimal("0.10") + Decimal("400000000") * Decimal("0.20")
        assert Decimal(r["tax"]) == expected.quantize(Decimal("1"))

    def test_with_spouse_deduction(self):
        """15억 상속, 배우자 5억: 일괄 5억 + 배우자 5억 = 10억 공제 → 과세 5억."""
        r = call(gross_estate="1500000000", spouse_inheritance="500000000", year=2026)
        ded = r["deductions"]
        assert Decimal(ded["general"]) == Decimal("500000000")
        assert Decimal(ded["spouse"])  == Decimal("500000000")
        assert Decimal(r["taxable_base"]) == Decimal("500000000")

    def test_spouse_cap_30억(self):
        """배우자 실제 40억 상속해도 공제는 30억으로 캡."""
        r = call(gross_estate="10000000000", spouse_inheritance="4000000000", year=2026)
        assert Decimal(r["deductions"]["spouse"]) == Decimal("3000000000")

    def test_spouse_floor_5억(self):
        """배우자 실제 1000만 상속 → 최소 5억 공제."""
        r = call(gross_estate="1000000000", spouse_inheritance="10000000", year=2026)
        assert Decimal(r["deductions"]["spouse"]) == Decimal("500000000")

    def test_basic_deduction_option(self):
        """use_lump_sum=False, 인적공제 없음 → 기초공제 2억만 적용."""
        r = call(
            gross_estate="500000000", spouse_inheritance="0",
            year=2026, use_lump_sum=False,
        )
        assert Decimal(r["deductions"]["general"]) == Decimal("200000000")

    def test_spouse_exceeds_gross_raises(self):
        with pytest.raises(InvalidInputError):
            call(gross_estate="1000000", spouse_inheritance="10000000", year=2026)

    def test_negative_raises(self):
        with pytest.raises(InvalidInputError):
            call(gross_estate="-1", spouse_inheritance="0", year=2026)

    def test_trace_present(self):
        r = call(gross_estate="1000000000", spouse_inheritance="0", year=2026)
        assert r["trace"]["tool"] == "tax.kr_inheritance"


class TestKrInheritanceSpouse:
    def test_surviving_spouse_without_inheritance_gets_5억(self):
        """제19조제4항: 배우자 생존·실제 상속 0 → 5억. 15억 - 10억 = 과세 5억 → 9,000만."""
        r = call(
            gross_estate="1500000000", spouse_inheritance="0", year=2026,
            has_spouse=True,
        )
        assert Decimal(r["deductions"]["spouse"]) == Decimal("500000000")
        assert Decimal(r["taxable_base"]) == Decimal("500000000")
        assert Decimal(r["tax"]) == Decimal("90000000")

    def test_legal_share_cap(self):
        """실제 20억, 법정상속분 한도 9억 → 배우자공제 9억. 30억 - 14억 = 16억 → 2.4억 + 6억 x 40% = 4.8억."""
        r = call(
            gross_estate="3000000000", spouse_inheritance="2000000000", year=2026,
            spouse_legal_share_cap="900000000",
        )
        assert Decimal(r["deductions"]["spouse"]) == Decimal("900000000")
        assert Decimal(r["taxable_base"]) == Decimal("1600000000")
        assert Decimal(r["tax"]) == Decimal("480000000")

    def test_spouse_sole_heir_excludes_lump_sum(self):
        """제21조제2항: 배우자 단독상속 40억 → 기초 2억 + 배우자 30억. 과세 8억 → 9천만 + 3억 x 30% = 1.8억."""
        r = call(
            gross_estate="4000000000", spouse_inheritance="4000000000", year=2026,
            spouse_sole_heir=True,
        )
        assert Decimal(r["deductions"]["general"]) == Decimal("200000000")
        assert Decimal(r["taxable_base"]) == Decimal("800000000")
        assert Decimal(r["tax"]) == Decimal("180000000")

    def test_has_spouse_false_with_inheritance_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                gross_estate="1000000000", spouse_inheritance="100000000", year=2026,
                has_spouse=False,
            )

    def test_sole_heir_without_spouse_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                gross_estate="1000000000", spouse_inheritance="0", year=2026,
                spouse_sole_heir=True,
            )


class TestKrInheritancePersonal:
    def test_basic_plus_personal_when_not_lump_sum(self):
        """자녀 2명 1억 + 미성년 10년 1억 + 65세 이상 1명 5천만 = 2.5억; 기초 포함 4.5억."""
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            use_lump_sum=False, children_count=2, minor_years_total=10, elderly_count=1,
        )
        assert Decimal(r["deductions"]["personal"]) == Decimal("250000000")
        assert Decimal(r["deductions"]["general"]) == Decimal("450000000")

    def test_lump_sum_takes_larger(self):
        """기초 + 인적 4.5억 < 일괄 5억 → 5억."""
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            children_count=2, minor_years_total=10, elderly_count=1,
        )
        assert Decimal(r["deductions"]["general"]) == Decimal("500000000")

    def test_basic_plus_personal_exceeds_lump_sum(self):
        """자녀 3명 1.5억 + 미성년 15년 1.5억 + 65세 1명 5천만 + 장애인 기대여명 5년 5천만 = 4억; 기초 포함 6억."""
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            children_count=3, minor_years_total=15, elderly_count=1,
            disabled_life_years_total=5,
        )
        assert Decimal(r["deductions"]["general"]) == Decimal("600000000")
        assert Decimal(r["taxable_base"]) == Decimal("400000000")

    def test_negative_count_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                gross_estate="1000000000", spouse_inheritance="0", year=2026,
                children_count=-1,
            )


class TestKrInheritanceDeductionLimit:
    def test_bequest_to_non_heirs_limits_deduction(self):
        """과세가액 10억, 상속인 아닌 자 유증 6억 → 한도 4억. 과세 6억 → 9천만 + 1억 x 30% = 1.2억."""
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            bequest_to_non_heirs="600000000",
        )
        assert Decimal(r["deductions"]["limit"]) == Decimal("400000000")
        assert Decimal(r["deductions"]["total"]) == Decimal("400000000")
        assert Decimal(r["tax"]) == Decimal("120000000")

    def test_pre_gift_limits_deduction_above_5억(self):
        """과세가액 10억, 가산 사전증여 7억 → 한도 3억. 과세 7억 → 9천만 + 2억 x 30% = 1.5억."""
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            pre_gift_added="700000000",
        )
        assert Decimal(r["deductions"]["total"]) == Decimal("300000000")
        assert Decimal(r["tax"]) == Decimal("150000000")

    def test_pre_gift_ignored_at_or_below_5억(self):
        """제24조 단서: 과세가액 5억 이하면 제3호 차감 없음 → 일괄 5억, 과세 0."""
        r = call(
            gross_estate="500000000", spouse_inheritance="0", year=2026,
            pre_gift_added="300000000",
        )
        assert Decimal(r["deductions"]["total"]) == Decimal("500000000")
        assert Decimal(r["tax"]) == Decimal("0")

    def test_renounced_inheritance_limits_deduction(self):
        """상속포기로 후순위가 받은 8억 → 한도 2억. 과세 8억 → 9천만 + 3억 x 30% = 1.8억."""
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            renounced_inheritance="800000000",
        )
        assert Decimal(r["taxable_base"]) == Decimal("800000000")
        assert Decimal(r["tax"]) == Decimal("180000000")


class TestKrInheritanceFilingCredit:
    def test_filing_credit_3pct(self):
        """10억, 배우자 없음: 산출 9,000만, 신고세액공제 270만 → 8,730만."""
        r = call(gross_estate="1000000000", spouse_inheritance="0", year=2026)
        assert Decimal(r["filing_credit"]) == Decimal("2700000")
        assert Decimal(r["tax_after_filing_credit"]) == Decimal("87300000")

    def test_no_filing_credit_when_not_filed(self):
        r = call(
            gross_estate="1000000000", spouse_inheritance="0", year=2026,
            timely_filing=False,
        )
        assert Decimal(r["filing_credit"]) == Decimal("0")
        assert Decimal(r["tax_after_filing_credit"]) == Decimal("90000000")
