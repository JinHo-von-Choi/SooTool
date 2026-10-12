"""Tests for accounting.ratios."""
from __future__ import annotations

from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("accounting.ratios", **kwargs)


class TestRatios:
    def test_textbook_example(self):
        """유동자산 5000, 유동부채 2000, 재고 1000 등 표준 예시."""
        r = call(
            current_assets="5000", current_liabilities="2000", inventory="1000",
            total_assets="10000", total_liabilities="4000", total_equity="6000",
            net_income="500", revenue="8000",
        )
        # 유동비율 = 5000/2000 = 2.5
        assert Decimal(r["current_ratio"]) == Decimal("2.5")
        # 당좌비율 = (5000-1000)/2000 = 2.0
        assert Decimal(r["quick_ratio"]) == Decimal("2.0")
        # 부채비율 = 4000/6000 = 0.6667
        assert Decimal(r["debt_to_equity"]) == Decimal("0.6667")
        # 자기자본비율 = 6000/10000 = 0.6
        assert Decimal(r["equity_ratio"]) == Decimal("0.6")
        # ROE = 500/6000 = 0.0833
        assert Decimal(r["roe"]) == Decimal("0.0833")
        # ROA = 500/10000 = 0.05
        assert Decimal(r["roa"]) == Decimal("0.0500")
        # 순이익률 = 500/8000 = 0.0625
        assert Decimal(r["net_margin"]) == Decimal("0.0625")

    def test_trace_present(self):
        r = call(
            current_assets="5000", current_liabilities="2000", inventory="1000",
            total_assets="10000", total_liabilities="4000", total_equity="6000",
            net_income="500", revenue="8000",
        )
        assert r["trace"]["tool"] == "accounting.ratios"

    def test_zero_liabilities_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                current_assets="1000", current_liabilities="0", inventory="0",
                total_assets="1000", total_liabilities="0", total_equity="1000",
                net_income="100", revenue="500",
            )

    def test_negative_input_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                current_assets="-1", current_liabilities="100", inventory="0",
                total_assets="1000", total_liabilities="0", total_equity="1000",
                net_income="100", revenue="500",
            )


@pytest.fixture
def ratio_inputs():
    return {
        "current_assets": "5000", "current_liabilities": "2000", "inventory": "1000",
        "total_assets": "10000", "total_liabilities": "4000", "total_equity": "6000",
        "net_income": "500", "revenue": "8000",
    }


@pytest.mark.parametrize("field", ["current_liabilities", "total_assets", "total_equity", "revenue"])
@pytest.mark.parametrize("zero", ["0", "-0", "0.000"])
def test_zero_denominators(ratio_inputs, field, zero):
    ratio_inputs[field] = zero
    with pytest.raises(InvalidInputError, match=field):
        call(**ratio_inputs)


@pytest.mark.parametrize(
    "field",
    ["current_assets", "current_liabilities", "inventory", "total_assets",
     "total_liabilities", "total_equity", "net_income", "revenue"],
)
@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "invalid", 0.1])
def test_invalid_numbers(ratio_inputs, field, value):
    ratio_inputs[field] = value
    with pytest.raises(InvalidInputError):
        call(**ratio_inputs)


@pytest.mark.parametrize("decimals", [-1, True, 1.5, "4", None])
def test_invalid_decimals(ratio_inputs, decimals):
    with pytest.raises(InvalidInputError):
        call(**ratio_inputs, decimals=decimals)


@pytest.mark.parametrize(
    ("income", "expected"), [("0", "0.0000"), ("-500", "-0.0625")],
)
def test_zero_and_negative_profit(ratio_inputs, income, expected):
    ratio_inputs["net_income"] = income
    assert call(**ratio_inputs)["net_margin"] == expected


def test_zero_assets_and_inventory(ratio_inputs):
    ratio_inputs.update(current_assets="0", inventory="0", total_liabilities="0")
    result = call(**ratio_inputs)
    assert result["current_ratio"] == "0.0000"
    assert result["quick_ratio"] == "0.0000"
    assert result["debt_ratio"] == "0.0000"


@pytest.mark.parametrize(
    ("assets", "expected"), [("1", "0.062"), ("3", "0.188")],
)
def test_half_even_ties(ratio_inputs, assets, expected):
    ratio_inputs.update(current_assets=assets, current_liabilities="16", inventory="0")
    assert call(**ratio_inputs, decimals=3)["current_ratio"] == expected


def test_zero_decimal_rounding(ratio_inputs):
    assert call(**ratio_inputs, decimals=0)["current_ratio"] == "2"


def test_precision_and_caller_context_isolation(ratio_inputs):
    ratio_inputs.update(
        current_assets="1.000000000000000003", inventory="1.000000000000000001",
        current_liabilities="1",
    )
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        context.Emax = 9
        context.Emin = -9
        context.clear_flags()
        result = call(**ratio_inputs, decimals=18)
        assert context.prec == 6
        assert context.rounding == ROUND_UP
        assert context.traps[Inexact]
        assert context.Emax == 9
        assert context.Emin == -9
        assert not any(context.flags.values())
    assert result["current_ratio"] == "1.000000000000000003"
    assert Decimal(result["quick_ratio"]) == Decimal("0.000000000000000002")
    assert result["debt_to_equity"] == "0.666666666666666667"
    assert result["trace"]["output"]["quick_ratio"] == result["quick_ratio"]


@pytest.mark.parametrize("kwargs", [{"current_assets": "1e100"}, {"decimals": 100}])
def test_unrepresentable_ratios_raise_domain_error(ratio_inputs, kwargs):
    ratio_inputs.update(kwargs)
    with pytest.raises(InvalidInputError, match="Decimal"):
        call(**ratio_inputs)
