"""Tests for accounting.dupont_3 and dupont_5."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestDupont3:
    def test_identity(self):
        """NM * TAT * EM = ROE"""
        r = REGISTRY.invoke(
            "accounting.dupont_3",
            net_income="100", revenue="1000",
            total_assets="2000", total_equity="500",
        )
        nm  = Decimal(r["net_margin"])
        tat = Decimal(r["asset_turnover"])
        em  = Decimal(r["equity_multiplier"])
        roe = Decimal(r["roe"])
        # 100/1000 * 1000/2000 * 2000/500 = 0.1*0.5*4 = 0.2
        assert nm == Decimal("0.100000")
        assert tat == Decimal("0.500000")
        assert em == Decimal("4.000000")
        assert roe == Decimal("0.200000")

    def test_zero_equity_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "accounting.dupont_3",
                net_income="100", revenue="1000",
                total_assets="2000", total_equity="0",
            )


class TestDupont5:
    def test_identity(self):
        """(NI/EBT)(EBT/EBIT)(EBIT/Rev)(Rev/TA)(TA/TE) = ROE"""
        r = REGISTRY.invoke(
            "accounting.dupont_5",
            net_income="80", pretax_income="100", ebit="150",
            revenue="1000", total_assets="2000", total_equity="500",
        )
        roe = Decimal(r["roe"])
        # (80/100)(100/150)(150/1000)(1000/2000)(2000/500) = 0.8*0.667*0.15*0.5*4 = 0.16
        assert abs(roe - Decimal("0.160000")) < Decimal("0.000001")

    def test_zero_ebit_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "accounting.dupont_5",
                net_income="80", pretax_income="100", ebit="0",
                revenue="1000", total_assets="2000", total_equity="500",
            )
