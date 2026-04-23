"""Tests for accounting.income_statement."""
from __future__ import annotations

from decimal import Decimal

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
