"""Tests for realestate.kr_comprehensive."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("realestate.kr_comprehensive", **kwargs)


class TestComprehensive:
    def test_1house_below_threshold_zero(self):
        """1주택 10억: 12억 공제 기준 미달 → 세액 0."""
        r = call(total_published_price="1000000000", year=2026, house_count=1)
        assert Decimal(r["total_tax"]) == Decimal("0")

    def test_1house_20억(self):
        """1주택 공시가 20억: 공제 12억, 과세표준 = (20-12) * 0.6 = 4.8억
           1주택 구간: 3억*0.5% + 1.8억*0.7% = 150만 + 126만 = 276만
        """
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert Decimal(r["taxable_base"]) == Decimal("480000000")
        expected_base = Decimal("300000000") * Decimal("0.005") \
                      + Decimal("180000000") * Decimal("0.007")
        assert Decimal(r["base_tax"]) == expected_base.quantize(Decimal("1"))

    def test_multi_house_uses_9억_deduction(self):
        r = call(total_published_price="2000000000", year=2026, house_count=3)
        assert Decimal(r["deduction"]) == Decimal("900000000")

    def test_multi_house_higher_rate(self):
        """다주택 20억: 공제 9억, 과세표준 = (20-9)*0.6 = 6.6억
           다주택 3억*0.5% + 3억*0.7% + 0.6억*1.0% = 150만+210만+60만 = 420만
        """
        r = call(total_published_price="2000000000", year=2026, house_count=3)
        assert Decimal(r["taxable_base"]) == Decimal("660000000")
        expected = Decimal("300000000") * Decimal("0.005") \
                 + Decimal("300000000") * Decimal("0.007") \
                 + Decimal("60000000")  * Decimal("0.010")
        assert Decimal(r["base_tax"]) == expected.quantize(Decimal("1"))

    def test_rural_special_is_20pct(self):
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert Decimal(r["rural_tax"]) <= Decimal(r["base_tax"]) * Decimal("0.20")

    def test_zero_count_raises(self):
        with pytest.raises(InvalidInputError):
            call(total_published_price="1000000000", year=2026, house_count=0)

    def test_zero_price_raises(self):
        with pytest.raises(InvalidInputError):
            call(total_published_price="0", year=2026, house_count=1)

    def test_trace(self):
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert r["trace"]["tool"] == "realestate.kr_comprehensive"
