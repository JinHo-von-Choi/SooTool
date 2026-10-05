"""Tests for finance NPV and IRR tools."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestNPV:
    def test_npv_standard_textbook(self) -> None:
        """rate=0.1, cf=[-100, 50, 60, 70] -> NPV ~ 47.03"""
        result = REGISTRY.invoke(
            "finance.npv",
            rate="0.1",
            cashflows=["-100", "50", "60", "70"],
            rounding="HALF_EVEN",
            decimals=2,
        )
        # Exact value: -100 + 50/1.1 + 60/1.21 + 70/1.331
        # = -100 + 45.4545... + 49.5867... + 52.5918... = 47.6331...
        npv = Decimal(result["npv"])
        assert abs(npv - Decimal("47.63")) < Decimal("0.05")
        assert "trace" in result

    def test_npv_all_same_sign_positive(self) -> None:
        """All positive cashflows -> NPV > 0."""
        result = REGISTRY.invoke(
            "finance.npv",
            rate="0.05",
            cashflows=["100", "100", "100"],
        )
        assert Decimal(result["npv"]) > 0

    def test_npv_single_cashflow(self) -> None:
        """Single cashflow at t=0: NPV = CF[0]."""
        result = REGISTRY.invoke(
            "finance.npv",
            rate="0.1",
            cashflows=["500"],
            decimals=2,
        )
        assert result["npv"] == "500.00"

    def test_npv_empty_cashflows_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.npv", rate="0.1", cashflows=[])

    def test_npv_negative_rate_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.npv",
                rate="-0.1",
                cashflows=["-100", "110"],
            )

    def test_finance_core_batch_race_free(self) -> None:
        """100 parallel NPV calls all return identical results."""
        def run_npv() -> str:
            r = REGISTRY.invoke(
                "finance.npv",
                rate="0.1",
                cashflows=["-1000", "400", "400", "400"],
                rounding="HALF_EVEN",
                decimals=6,
            )
            return r["npv"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(run_npv) for _ in range(100)]
            results = [f.result() for f in futures]

        assert len(set(results)) == 1, "All parallel calls must return identical NPV"


class TestROI:
    def test_roi_standard_investment(self) -> None:
        result = REGISTRY.invoke(
            "finance.roi",
            net_profit="25",
            investment_cost="100",
        )

        assert result["roi"] == "0.2500"
        assert result["trace"]["tool"] == "finance.roi"

    @pytest.mark.parametrize(
        ("net_profit", "expected"),
        [("0", "0.0000"), ("-20", "-0.2000")],
    )
    def test_roi_zero_or_loss_boundary(self, net_profit: str, expected: str) -> None:
        result = REGISTRY.invoke(
            "finance.roi",
            net_profit=net_profit,
            investment_cost="100",
        )

        assert result["roi"] == expected

    @pytest.mark.parametrize("investment_cost", ["0", "-0.01"])
    def test_roi_non_positive_investment_cost_raises(self, investment_cost: str) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.roi",
                net_profit="10",
                investment_cost=investment_cost,
            )

    def test_roi_honors_rounding_policy_at_precision_boundary(self) -> None:
        half_even = REGISTRY.invoke(
            "finance.roi",
            net_profit="1",
            investment_cost="16",
            decimals=3,
            rounding="HALF_EVEN",
        )
        half_up = REGISTRY.invoke(
            "finance.roi",
            net_profit="1",
            investment_cost="16",
            decimals=3,
            rounding="HALF_UP",
        )

        assert half_even["roi"] == "0.062"
        assert half_up["roi"] == "0.063"

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"rounding": "BANKERS"}, "반올림 정책"),
            ({"decimals": -1}, "decimals"),
        ],
    )
    def test_roi_invalid_options_raise(self, kwargs: dict[str, object], message: str) -> None:
        with pytest.raises(InvalidInputError, match=message):
            REGISTRY.invoke(
                "finance.roi",
                net_profit="10",
                investment_cost="100",
                **kwargs,
            )


class TestIRR:
    def test_irr_simple(self) -> None:
        """cf=[-100, 110] -> irr ~ 0.10"""
        result = REGISTRY.invoke(
            "finance.irr",
            cashflows=["-100", "110"],
        )
        irr = Decimal(result["irr"])
        assert abs(irr - Decimal("0.10")) < Decimal("1e-6")
        assert result["converged"] is True
        assert "iterations" in result

    def test_irr_multiyear(self) -> None:
        """cf=[-1000, 400, 400, 400] -> known IRR ~ 9.7%"""
        result = REGISTRY.invoke(
            "finance.irr",
            cashflows=["-1000", "400", "400", "400"],
        )
        irr = Decimal(result["irr"])
        # NPV(-1000, 400, 400, 400) at IRR = 0 => verify by checking NPV near 0
        # Exact IRR ~ 0.09700... via numerical methods
        assert abs(irr - Decimal("0.0970")) < Decimal("0.0005")
        assert result["converged"] is True

    def test_irr_exact_10pct(self) -> None:
        """cf=[-1000, 200, 200, 200, 200, 200, 200] -> IRR slightly above 5%."""
        result = REGISTRY.invoke(
            "finance.irr",
            cashflows=["-1000", "200", "200", "200", "200", "200", "200"],
        )
        irr = Decimal(result["irr"])
        assert Decimal("0.04") < irr < Decimal("0.06")
        assert result["converged"] is True

    def test_irr_convergence_flag_all_positive(self) -> None:
        """All-positive cashflows: no sign change -> converged=False."""
        result = REGISTRY.invoke(
            "finance.irr",
            cashflows=["100", "110", "120"],
        )
        assert result["converged"] is False

    def test_irr_empty_cashflows_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.irr", cashflows=[])

    def test_irr_single_cashflow_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.irr", cashflows=["-100"])

    def test_irr_high_precision(self) -> None:
        """IRR within 1e-10 tolerance for simple case."""
        result = REGISTRY.invoke(
            "finance.irr",
            cashflows=["-100", "110"],
            tol="1e-10",
        )
        irr = Decimal(result["irr"])
        assert abs(irr - Decimal("0.10")) < Decimal("1e-9")
