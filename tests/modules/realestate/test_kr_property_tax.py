"""Tests for realestate.kr_property_tax."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("realestate.kr_property_tax", **kwargs)


class TestPropertyTax:
    def test_500M_published(self):
        """공시가 5억 → 과세표준 3억; 6000만*0.1% + 9000만*0.15% + 1.5억*0.25% = 6만+13.5만+37.5만 = 57만"""
        r = call(published_price="500000000", year=2026, include_urban=False)
        # 과세표준 = 5억 * 0.6 = 3억
        assert Decimal(r["taxable_base"]) == Decimal("300000000")
        expected_prop = (
            Decimal("60000000")  * Decimal("0.001")
            + Decimal("90000000") * Decimal("0.0015")
            + Decimal("150000000") * Decimal("0.0025")
        )
        assert Decimal(r["property_tax"]) == expected_prop.quantize(Decimal("1"))

    def test_with_urban_surcharge(self):
        r = call(published_price="500000000", year=2026, include_urban=True)
        assert Decimal(r["surcharges"]["urban_area"]) > Decimal("0")

    def test_local_edu_is_20pct_of_property_tax(self):
        r = call(published_price="500000000", year=2026, include_urban=False)
        pt = Decimal(r["property_tax"])
        le = Decimal(r["surcharges"]["local_edu"])
        # 20% with FLOOR rounding
        assert le <= pt * Decimal("0.20")
        assert le >= pt * Decimal("0.20") - Decimal("1")

    def test_zero_published_raises(self):
        with pytest.raises(InvalidInputError):
            call(published_price="0", year=2026)

    def test_trace(self):
        r = call(published_price="500000000", year=2026)
        assert r["trace"]["tool"] == "realestate.kr_property_tax"
        assert "policy_version" in r
