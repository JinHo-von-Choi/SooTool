"""Tests for tax.kr_inheritance."""
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
        """use_lump_sum=False → 기초공제 2억만 적용."""
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
