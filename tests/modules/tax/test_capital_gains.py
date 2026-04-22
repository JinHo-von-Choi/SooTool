"""Tests for tax.capital_gains_kr tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call_capital_gains(**kwargs):
    return REGISTRY.invoke("tax.capital_gains_kr", **kwargs)


class TestCapitalGainsKr:
    def test_non_1house_5years(self):
        """일반 부동산, 5년 보유 → LTCT 10% (5년: 10%)."""
        result = call_capital_gains(
            acquisition_price="100000000",
            sale_price="200000000",
            holding_years=5,
            is_one_house=False,
            year=2026,
        )
        gain          = Decimal(result["gain"])
        ltct_deduct   = Decimal(result["ltct_deduction"])
        taxable_gain  = Decimal(result["taxable_gain"])

        assert gain == Decimal("100000000")
        # LTCT 10%: deduction = 10,000,000
        assert ltct_deduct == Decimal("10000000")
        # taxable = 90,000,000
        assert taxable_gain == Decimal("90000000")
        assert int(result["tax"]) > 0

    def test_non_1house_3years(self):
        """일반 부동산, 3년 보유 → LTCT 6%."""
        result = call_capital_gains(
            acquisition_price="200000000",
            sale_price="300000000",
            holding_years=3,
            is_one_house=False,
            year=2026,
        )
        gain        = Decimal(result["gain"])
        ltct_deduct = Decimal(result["ltct_deduction"])

        assert gain == Decimal("100000000")
        assert ltct_deduct == gain * Decimal("0.06")

    def test_non_1house_2years_no_deduction(self):
        """일반 부동산, 2년 보유 → 장기보유특별공제 없음."""
        result = call_capital_gains(
            acquisition_price="100000000",
            sale_price="200000000",
            holding_years=2,
            is_one_house=False,
            year=2026,
        )
        assert result["ltct_deduction"] == "0"
        assert result["taxable_gain"] == result["gain"]

    def test_non_1house_15years_max30(self):
        """일반 부동산, 15년 보유 → LTCT 30% (최대)."""
        result = call_capital_gains(
            acquisition_price="100000000",
            sale_price="200000000",
            holding_years=15,
            is_one_house=False,
            year=2026,
        )
        ltct_deduct = Decimal(result["ltct_deduction"])
        gain        = Decimal(result["gain"])
        assert ltct_deduct == gain * Decimal("0.30")

    def test_non_1house_20years_capped_at_30(self):
        """일반 부동산, 20년 보유 → 여전히 30% (15년 이상 최대)."""
        result = call_capital_gains(
            acquisition_price="100000000",
            sale_price="200000000",
            holding_years=20,
            is_one_house=False,
            year=2026,
        )
        ltct_deduct = Decimal(result["ltct_deduction"])
        gain        = Decimal(result["gain"])
        assert ltct_deduct == gain * Decimal("0.30")

    def test_1house_10years_80pct(self):
        """1세대1주택, 10년 이상 → LTCT 80%."""
        result = call_capital_gains(
            acquisition_price="300000000",
            sale_price="700000000",
            holding_years=10,
            is_one_house=True,
            year=2026,
        )
        gain        = Decimal(result["gain"])
        ltct_deduct = Decimal(result["ltct_deduction"])
        assert gain == Decimal("400000000")
        assert ltct_deduct == gain * Decimal("0.80")

    def test_1house_15years_over_80pct(self):
        """1세대1주택, 15년 이상 → 여전히 80% (최대)."""
        result = call_capital_gains(
            acquisition_price="100000000",
            sale_price="500000000",
            holding_years=15,
            is_one_house=True,
            year=2026,
        )
        gain        = Decimal(result["gain"])
        ltct_deduct = Decimal(result["ltct_deduction"])
        assert ltct_deduct == gain * Decimal("0.80")

    def test_no_gain_returns_zero_tax(self):
        """양도차익 없음 → 세액 0."""
        result = call_capital_gains(
            acquisition_price="200000000",
            sale_price="200000000",
            holding_years=5,
            is_one_house=False,
            year=2026,
        )
        assert result["tax"] == "0"
        assert result["gain"] == "0"

    def test_loss_returns_zero_tax(self):
        """양도손실 → 세액 0."""
        result = call_capital_gains(
            acquisition_price="200000000",
            sale_price="100000000",
            holding_years=5,
            is_one_house=False,
            year=2026,
        )
        assert result["tax"] == "0"

    def test_negative_acquisition_raises(self):
        with pytest.raises(InvalidInputError):
            call_capital_gains(
                acquisition_price="-1",
                sale_price="200000000",
                holding_years=5,
                is_one_house=False,
                year=2026,
            )

    def test_unsupported_year_raises(self):
        with pytest.raises(UnsupportedPolicyError):
            call_capital_gains(
                acquisition_price="100000000",
                sale_price="200000000",
                holding_years=5,
                is_one_house=False,
                year=2099,
            )

    def test_policy_version_returned(self):
        result = call_capital_gains(
            acquisition_price="100000000",
            sale_price="200000000",
            holding_years=5,
            is_one_house=False,
            year=2026,
        )
        pv = result["policy_version"]
        assert "year" in pv
        assert pv["year"] == 2026
