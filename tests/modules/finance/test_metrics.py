"""Tests for finance NPV and IRR tools."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal, localcontext

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



class TestCAGR:
    @pytest.mark.parametrize(
        ("ending_value", "expected"),
        [
            ("1." + "0" * 49 + "1", Decimal("1e-50")),
            ("0." + "9" * 50, Decimal("-1e-50")),
            ("0", Decimal("-1")),
            ("1", Decimal("0")),
        ],
    )
    def test_single_period_preserves_small_changes(self, ending_value, expected) -> None:
        result = REGISTRY.invoke(
            "finance.cagr", beginning_value="1", ending_value=ending_value,
            periods=1, decimals=50 if abs(expected) < 1 else 6,
        )
        assert Decimal(result["cagr"]) == expected
        assert Decimal(result["trace"]["output"]) == expected

    @pytest.mark.parametrize("field", ["beginning_value", "ending_value"])
    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "bad", 1.5])
    def test_rejects_invalid_values(self, field, value) -> None:
        kwargs = {"beginning_value": "100", "ending_value": "110", "periods": 2}
        kwargs[field] = value
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.cagr", **kwargs)

    @pytest.mark.parametrize("field", ["periods", "decimals"])
    @pytest.mark.parametrize("value", [True, False, 1.5, "2", None, -1])
    def test_rejects_invalid_integer_arguments(self, field, value) -> None:
        kwargs = {"beginning_value": "100", "ending_value": "110", "periods": 2}
        kwargs[field] = value
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.cagr", **kwargs)

    def test_cagr_standard_compound_growth(self) -> None:
        result = REGISTRY.invoke(
            "finance.cagr",
            beginning_value="1000",
            ending_value="1331",
            periods=3,
        )

        assert result["cagr"] == "0.100000"
        assert result["trace"]["tool"] == "finance.cagr"

    @pytest.mark.parametrize(
        ("ending_value", "expected"),
        [("0", "-1.000000"), ("100", "0.000000")],
    )
    def test_cagr_zero_and_no_growth_boundaries(
        self,
        ending_value: str,
        expected: str,
    ) -> None:
        result = REGISTRY.invoke(
            "finance.cagr",
            beginning_value="100",
            ending_value=ending_value,
            periods=5,
        )

        assert result["cagr"] == expected

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"beginning_value": "0", "ending_value": "100", "periods": 1},
            {"beginning_value": "-1", "ending_value": "100", "periods": 1},
            {"beginning_value": "100", "ending_value": "-1", "periods": 1},
            {"beginning_value": "100", "ending_value": "110", "periods": 0},
            {"beginning_value": "100", "ending_value": "110", "periods": -1},
        ],
    )
    def test_cagr_invalid_inputs_raise(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.cagr", **kwargs)

    def test_cagr_honors_rounding_policy_at_precision_boundary(self) -> None:
        half_even = REGISTRY.invoke(
            "finance.cagr",
            beginning_value="16",
            ending_value="17",
            periods=1,
            decimals=3,
            rounding="HALF_EVEN",
        )
        half_up = REGISTRY.invoke(
            "finance.cagr",
            beginning_value="16",
            ending_value="17",
            periods=1,
            decimals=3,
            rounding="HALF_UP",
        )

        assert half_even["cagr"] == "0.062"
        assert half_up["cagr"] == "0.063"


class TestPaybackPeriod:
    @pytest.mark.parametrize(
        ("last_cashflow", "expected", "recovered"),
        [("0", None, False), ("0.01", "2.500000", True), ("0.005", "3.000000", True)],
    )
    def test_large_cashflows_preserve_small_unrecovered_balance(
        self, last_cashflow: str, expected: str | None, recovered: bool,
    ) -> None:
        almost_recovered = "1" + "0" * 60
        investment = almost_recovered + ".005"
        result = REGISTRY.invoke(
            "finance.payback_period",
            cashflows=["-" + investment, "0", almost_recovered, last_cashflow],
        )

        assert result["payback_period"] == expected
        assert result["recovered"] is recovered

    def test_precision_does_not_depend_on_caller_context(self) -> None:
        with localcontext() as context:
            context.prec = 6
            result = REGISTRY.invoke(
                "finance.payback_period", cashflows=["-1", "3"], decimals=30,
            )
            assert context.prec == 6

        assert result["payback_period"] == "0." + "3" * 30
        assert result["trace"]["output"] == result["payback_period"]

    def test_negative_and_zero_intermediate_cashflows(self) -> None:
        result = REGISTRY.invoke(
            "finance.payback_period", cashflows=["-100", "0", "-20", "240"],
        )

        assert result["payback_period"] == "2.500000"

    @pytest.mark.parametrize("decimals", [True, False, 1.5, "2", None, -1])
    def test_invalid_decimal_places_raise(self, decimals: object) -> None:
        with pytest.raises(InvalidInputError, match="decimals"):
            REGISTRY.invoke(
                "finance.payback_period", cashflows=["-100", "200"], decimals=decimals,
            )

    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "bad", 1.5])
    @pytest.mark.parametrize("index", [0, 1])
    def test_invalid_cashflows_raise(self, value: object, index: int) -> None:
        cashflows = ["-100", "200"]
        cashflows[index] = value
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.payback_period", cashflows=cashflows)

    def test_fractional_recovery_period(self) -> None:
        result = REGISTRY.invoke(
            "finance.payback_period",
            cashflows=["-1000", "300", "400", "500"],
            rounding="HALF_EVEN",
            decimals=4,
        )

        assert result["payback_period"] == "2.6000"
        assert result["recovered"] is True
        assert result["trace"]["output"] == "2.6000"

    def test_exact_period_boundary(self) -> None:
        result = REGISTRY.invoke(
            "finance.payback_period",
            cashflows=["-100", "40", "60", "25"],
            decimals=2,
        )

        assert result["payback_period"] == "2.00"
        assert result["recovered"] is True

    def test_unrecovered_investment_returns_none(self) -> None:
        result = REGISTRY.invoke(
            "finance.payback_period",
            cashflows=["-100", "30", "40"],
        )

        assert result["payback_period"] is None
        assert result["recovered"] is False
        assert result["trace"]["output"] == "not_recovered"

    def test_honors_rounding_policy_at_precision_boundary(self) -> None:
        half_even = REGISTRY.invoke(
            "finance.payback_period",
            cashflows=["-1", "8"],
            rounding="HALF_EVEN",
            decimals=2,
        )
        half_up = REGISTRY.invoke(
            "finance.payback_period",
            cashflows=["-1", "8"],
            rounding="HALF_UP",
            decimals=2,
        )

        assert half_even["payback_period"] == "0.12"
        assert half_up["payback_period"] == "0.13"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"cashflows": []},
            {"cashflows": ["-100"]},
            {"cashflows": ["0", "100"]},
            {"cashflows": ["100", "-100"]},
            {"cashflows": ["-100", "NaN"]},
            {"cashflows": ["-100", "200"], "decimals": -1},
            {"cashflows": ["-100", "200"], "rounding": "INVALID"},
        ],
    )
    def test_invalid_inputs_raise(self, kwargs: dict[str, object]) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.payback_period", **kwargs)



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
