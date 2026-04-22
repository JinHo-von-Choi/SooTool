"""Tests for finance bond tools: bond_ytm and bond_duration."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestBondYTM:
    def test_bond_ytm_par(self) -> None:
        """price==face, coupon_rate=5% -> ytm ~ 5%."""
        result = REGISTRY.invoke(
            "finance.bond_ytm",
            price="1000",
            face="1000",
            coupon_rate="0.05",
            years=10,
            freq=2,
        )
        ytm = Decimal(result["ytm"])
        assert abs(ytm - Decimal("0.05")) < Decimal("1e-6")
        assert result["converged"] is True
        assert "iterations" in result

    def test_bond_ytm_discount(self) -> None:
        """Price < face -> ytm > coupon_rate."""
        result = REGISTRY.invoke(
            "finance.bond_ytm",
            price="950",
            face="1000",
            coupon_rate="0.05",
            years=10,
            freq=2,
        )
        ytm = Decimal(result["ytm"])
        assert ytm > Decimal("0.05")

    def test_bond_ytm_premium(self) -> None:
        """Price > face -> ytm < coupon_rate."""
        result = REGISTRY.invoke(
            "finance.bond_ytm",
            price="1050",
            face="1000",
            coupon_rate="0.05",
            years=10,
            freq=2,
        )
        ytm = Decimal(result["ytm"])
        assert ytm < Decimal("0.05")

    def test_bond_ytm_trace(self) -> None:
        result = REGISTRY.invoke(
            "finance.bond_ytm",
            price="1000",
            face="1000",
            coupon_rate="0.05",
            years=5,
            freq=2,
        )
        assert "trace" in result

    def test_bond_ytm_zero_coupon(self) -> None:
        """Zero coupon bond: price = face / (1 + ytm/freq)^(years*freq)."""
        # face=1000, price=500, years=10 -> ytm ~ (1000/500)^(1/10) - 1 = 7.18%
        result = REGISTRY.invoke(
            "finance.bond_ytm",
            price="500",
            face="1000",
            coupon_rate="0",
            years=10,
            freq=1,
        )
        ytm = Decimal(result["ytm"])
        expected = Decimal("2") ** (Decimal("1") / 10) - 1  # ~ 0.0718
        assert abs(ytm - expected) < Decimal("1e-5")

    def test_bond_ytm_invalid_price_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.bond_ytm",
                price="-100",
                face="1000",
                coupon_rate="0.05",
                years=5,
            )


class TestBondDuration:
    def test_bond_duration_zero_coupon(self) -> None:
        """Zero-coupon bond: Macaulay duration == years."""
        result = REGISTRY.invoke(
            "finance.bond_duration",
            face="1000",
            coupon_rate="0",
            years=5,
            ytm="0.05",
            freq=1,
        )
        mac = Decimal(result["macaulay"])
        assert abs(mac - Decimal("5")) < Decimal("1e-6")

    def test_bond_duration_modified_less_than_macaulay(self) -> None:
        """Modified duration < Macaulay duration for freq > 0."""
        result = REGISTRY.invoke(
            "finance.bond_duration",
            face="1000",
            coupon_rate="0.05",
            years=10,
            ytm="0.05",
            freq=2,
        )
        mac = Decimal(result["macaulay"])
        mod = Decimal(result["modified"])
        assert mod < mac

    def test_bond_duration_textbook_5pct_10y(self) -> None:
        """5% coupon, 10-year, 5% YTM semi-annual: macaulay ~ 7.99 years."""
        result = REGISTRY.invoke(
            "finance.bond_duration",
            face="1000",
            coupon_rate="0.05",
            years=10,
            ytm="0.05",
            freq=2,
        )
        mac = Decimal(result["macaulay"])
        mod = Decimal(result["modified"])
        # Well-known textbook value: macaulay ~ 7.99 for this bond
        assert Decimal("7.5") < mac < Decimal("8.5")
        assert mod < mac

    def test_bond_duration_trace(self) -> None:
        result = REGISTRY.invoke(
            "finance.bond_duration",
            face="1000",
            coupon_rate="0.05",
            years=5,
            ytm="0.05",
            freq=2,
        )
        assert "trace" in result
        assert result["trace"]["tool"] == "finance.bond_duration"
