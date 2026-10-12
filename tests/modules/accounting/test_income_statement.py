"""Tests for accounting.income_statement."""
from __future__ import annotations

from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("accounting.income_statement", **kwargs)


class TestIncomeStatement:
    def test_standard_flow(self):
        """매출 10000, COGS 6000, 판관비 2000, 법인세 400."""
        r = call(
            revenue="10000", cost_of_sales="6000",
            operating_expenses="2000", tax_expense="400",
        )
        assert Decimal(r["gross_profit"]) == Decimal("4000")
        assert Decimal(r["operating_income"]) == Decimal("2000")
        assert Decimal(r["pretax_income"]) == Decimal("2000")
        assert Decimal(r["net_income"]) == Decimal("1600")
        assert Decimal(r["gross_margin"]) == Decimal("0.400000")

    def test_with_interest_and_other(self):
        r = call(
            revenue="10000", cost_of_sales="6000",
            operating_expenses="1000",
            other_income="500", other_expenses="200",
            interest_expense="300", tax_expense="200",
        )
        # gross = 4000, op = 3000, pretax = 3000+500-200-300 = 3000, net = 2800
        assert Decimal(r["pretax_income"]) == Decimal("3000")
        assert Decimal(r["net_income"]) == Decimal("2800")

    def test_zero_revenue_margin_zero(self):
        r = call(revenue="0", cost_of_sales="0")
        assert r["gross_margin"] == "0"

    def test_negative_revenue_raises(self):
        with pytest.raises(InvalidInputError):
            call(revenue="-1", cost_of_sales="0")

    def test_trace(self):
        r = call(revenue="100", cost_of_sales="50")
        assert r["trace"]["tool"] == "accounting.income_statement"


@pytest.mark.parametrize(
    ("kwargs", "expected_income", "expected_margin"),
    [
        ({"revenue": "0", "cost_of_sales": "1"}, "-1", "0"),
        ({"revenue": "1", "cost_of_sales": "1"}, "0", "0.000000"),
        ({"revenue": "1", "cost_of_sales": "2"}, "-1", "-1.000000"),
    ],
)
def test_profit_boundaries(kwargs, expected_income, expected_margin):
    result = call(**kwargs)
    for field in ("gross_profit", "operating_income", "pretax_income", "net_income"):
        assert result[field] == expected_income
    for field in ("gross_margin", "operating_margin", "pretax_margin", "net_margin"):
        assert result[field] == expected_margin


@pytest.mark.parametrize(
    "field",
    [
        "revenue", "cost_of_sales", "operating_expenses", "other_income",
        "other_expenses", "interest_expense", "tax_expense",
    ],
)
@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "invalid", 0.1])
def test_invalid_line_items(field, value):
    inputs = {"revenue": "100", "cost_of_sales": "50", field: value}
    with pytest.raises(InvalidInputError):
        call(**inputs)


def test_negative_cost_of_sales_rejected():
    with pytest.raises(InvalidInputError):
        call(revenue="1", cost_of_sales="-0.01")


@pytest.mark.parametrize(
    ("cost_of_sales", "expected"),
    [("0.8765435", "0.123456"), ("0.8765425", "0.123458")],
)
def test_margin_half_even_ties(cost_of_sales, expected):
    with localcontext() as context:
        context.rounding = ROUND_UP
        result = call(revenue="1", cost_of_sales=cost_of_sales)
    assert result["net_margin"] == expected


def test_caller_context_does_not_change_profit_or_margins():
    inputs = {
        "revenue": "1.000000000000000003",
        "cost_of_sales": "1.000000000000000001",
        "operating_expenses": "0.000000000000000001",
    }
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        context.clear_flags()
        result = call(**inputs)
        assert context.prec == 6
        assert context.rounding == ROUND_UP
        assert context.traps[Inexact]
        assert not any(context.flags.values())
    assert Decimal(result["gross_profit"]) == Decimal("0.000000000000000002")
    assert Decimal(result["net_income"]) == Decimal("0.000000000000000001")
    assert result["net_margin"] == "0.000000"
    assert result["trace"]["output"]["net_income"] == result["net_income"]


def test_unrepresentable_margin_raises_domain_error():
    with pytest.raises(InvalidInputError, match="Decimal"):
        call(revenue="1e-100", cost_of_sales="1")
