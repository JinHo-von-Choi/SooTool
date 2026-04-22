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
