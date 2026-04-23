"""Tests for finance.futures_price, forward_price, option_payoff."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestFuturesPrice:
    def test_cost_of_carry(self):
        """S=100, r=0.05, T=1, q=0 → F ≈ 100 * e^0.05 ≈ 105.127"""
        r = REGISTRY.invoke(
            "finance.futures_price",
            spot="100", risk_free_rate="0.05", time_to_expiry="1",
        )
        val = float(r["futures_price"])
        assert abs(val - 105.1271) < 1e-3

    def test_dividend_reduces_futures(self):
        r_no_div = REGISTRY.invoke(
            "finance.futures_price",
            spot="100", risk_free_rate="0.05", time_to_expiry="1",
        )
        r_div = REGISTRY.invoke(
            "finance.futures_price",
            spot="100", risk_free_rate="0.05", time_to_expiry="1",
            dividend_yield="0.03",
        )
        assert Decimal(r_div["futures_price"]) < Decimal(r_no_div["futures_price"])

    def test_zero_time_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.futures_price",
                spot="100", risk_free_rate="0.05", time_to_expiry="0",
            )


class TestForwardPrice:
    def test_equivalence_to_futures(self):
        """Identical continuous-compounding inputs: forward == futures."""
        r1 = REGISTRY.invoke(
            "finance.forward_price",
            spot="100", risk_free_rate="0.03", time_to_expiry="2",
        )
        r2 = REGISTRY.invoke(
            "finance.futures_price",
            spot="100", risk_free_rate="0.03", time_to_expiry="2",
        )
        assert r1["forward_price"] == r2["futures_price"]


class TestOptionPayoff:
    def test_vanilla_call_itm(self):
        r = REGISTRY.invoke(
            "finance.option_payoff",
            option_type="vanilla", strike="100",
            spot_path=["110"], is_call=True,
        )
        assert Decimal(r["payoff"]) == Decimal("10")

    def test_vanilla_put_otm(self):
        r = REGISTRY.invoke(
            "finance.option_payoff",
            option_type="vanilla", strike="100",
            spot_path=["110"], is_call=False,
        )
        assert Decimal(r["payoff"]) == Decimal("0")

    def test_digital_call(self):
        r = REGISTRY.invoke(
            "finance.option_payoff",
            option_type="digital", strike="100",
            spot_path=["110"], is_call=True,
            digital_cash="5",
        )
        assert Decimal(r["payoff"]) == Decimal("5")

    def test_asian_call(self):
        """Asian arithmetic mean call: path [90,100,110] → mean 100, strike 95 → 5"""
        r = REGISTRY.invoke(
            "finance.option_payoff",
            option_type="asian", strike="95",
            spot_path=["90","100","110"], is_call=True,
        )
        assert Decimal(r["payoff"]) == Decimal("5")

    def test_barrier_up_and_out_knocked_out(self):
        """Up-and-out call: 경로 중 120 돌파 → knocked out → payoff 0"""
        r = REGISTRY.invoke(
            "finance.option_payoff",
            option_type="barrier", strike="100",
            spot_path=["110","125","115"],
            is_call=True, barrier="120", barrier_type="up_out",
        )
        assert r["activated"] is False
        assert Decimal(r["payoff"]) == Decimal("0")

    def test_barrier_up_and_in_activated(self):
        r = REGISTRY.invoke(
            "finance.option_payoff",
            option_type="barrier", strike="100",
            spot_path=["110","125","115"],
            is_call=True, barrier="120", barrier_type="up_in",
        )
        assert r["activated"] is True
        assert Decimal(r["payoff"]) == Decimal("15")

    def test_invalid_option_type_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.option_payoff",
                option_type="wonky", strike="100", spot_path=["100"],
            )

    def test_barrier_missing_params_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.option_payoff",
                option_type="barrier", strike="100", spot_path=["100"],
            )
