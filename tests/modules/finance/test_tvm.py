"""Tests for finance TVM tools: finance.pv and finance.fv."""
from __future__ import annotations

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestPV:
    def test_pv_textbook_5pct_10y(self) -> None:
        """PV of 1000 at 5% for 10 periods = 613.91"""
        result = REGISTRY.invoke(
            "finance.pv",
            future_value="1000",
            rate="0.05",
            periods=10,
            rounding="HALF_EVEN",
            decimals=2,
        )
        assert result["pv"] == "613.91"
        assert "trace" in result

    def test_pv_zero_rate(self) -> None:
        """At 0% rate, PV == FV."""
        result = REGISTRY.invoke(
            "finance.pv",
            future_value="500",
            rate="0",
            periods=5,
            rounding="HALF_EVEN",
            decimals=2,
        )
        assert result["pv"] == "500.00"

    def test_pv_one_period(self) -> None:
        """PV of 110 at 10% for 1 period = 100.00"""
        result = REGISTRY.invoke(
            "finance.pv",
            future_value="110",
            rate="0.1",
            periods=1,
            rounding="HALF_EVEN",
            decimals=2,
        )
        assert result["pv"] == "100.00"

    def test_pv_negative_rate_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.pv",
                future_value="1000",
                rate="-0.05",
                periods=10,
            )

    def test_pv_zero_periods_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.pv",
                future_value="1000",
                rate="0.05",
                periods=0,
            )

    def test_pv_trace_fields(self) -> None:
        result = REGISTRY.invoke(
            "finance.pv",
            future_value="1000",
            rate="0.05",
            periods=10,
        )
        trace = result["trace"]
        assert trace["tool"] == "finance.pv"
        assert "inputs" in trace
        assert "steps" in trace


class TestFV:
    def test_fv_textbook_5pct_10y(self) -> None:
        """FV of 1000 at 5% for 10 periods ~ 1628.89"""
        result = REGISTRY.invoke(
            "finance.fv",
            present_value="1000",
            rate="0.05",
            periods=10,
            rounding="HALF_EVEN",
            decimals=2,
        )
        assert result["fv"] == "1628.89"

    def test_fv_roundtrip(self) -> None:
        """fv(pv(X, r, n), r, n) == X within rounding tolerance."""
        original = "1000"
        pv_result = REGISTRY.invoke(
            "finance.pv",
            future_value=original,
            rate="0.07",
            periods=15,
            rounding="HALF_EVEN",
            decimals=10,
        )
        fv_result = REGISTRY.invoke(
            "finance.fv",
            present_value=pv_result["pv"],
            rate="0.07",
            periods=15,
            rounding="HALF_EVEN",
            decimals=2,
        )
        assert fv_result["fv"] == "1000.00"

    def test_fv_zero_rate(self) -> None:
        result = REGISTRY.invoke(
            "finance.fv",
            present_value="500",
            rate="0",
            periods=5,
            rounding="HALF_EVEN",
            decimals=2,
        )
        assert result["fv"] == "500.00"

    def test_fv_negative_rate_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.fv",
                present_value="1000",
                rate="-0.05",
                periods=5,
            )

    def test_fv_zero_periods_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.fv",
                present_value="1000",
                rate="0.05",
                periods=0,
            )
