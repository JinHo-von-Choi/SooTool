"""Tests for accounting depreciation tools."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.accounting  # ensure tools are registered
from sootool.core.registry import REGISTRY


class TestStraightLine:
    def test_straight_line_100_asset_5y_10_salvage(self) -> None:
        """cost=100, salvage=10, life=5 -> annual=18, year5 book_value_end=10"""
        result = REGISTRY.invoke(
            "accounting.depreciation_straight_line",
            cost="100",
            salvage="10",
            life_years=5,
            decimals=0,
            rounding="HALF_EVEN",
        )
        assert result["annual_expense"] == "18"
        schedule = result["schedule"]
        assert len(schedule) == 5
        assert schedule[4]["book_value_end"] == "10"
        assert schedule[0]["year"] == 1
        assert "trace" in result

    def test_straight_line_schedule_monotonic_decreasing(self) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_straight_line",
            cost="200",
            salvage="20",
            life_years=4,
            decimals=2,
            rounding="HALF_EVEN",
        )
        schedule = result["schedule"]
        for entry in schedule:
            assert "year" in entry
            assert "depreciation" in entry
            assert "book_value_end" in entry
        book_values = [Decimal(e["book_value_end"]) for e in schedule]
        for i in range(1, len(book_values)):
            assert book_values[i] < book_values[i - 1]

    def test_straight_line_trace(self) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_straight_line",
            cost="50",
            salvage="0",
            life_years=5,
            decimals=0,
            rounding="HALF_EVEN",
        )
        assert result["trace"]["tool"] == "accounting.depreciation_straight_line"


class TestDecliningBalance:
    def test_declining_balance_no_undershoot_salvage(self) -> None:
        """Declining balance must stop at salvage if it would go below."""
        result = REGISTRY.invoke(
            "accounting.depreciation_declining_balance",
            cost="1000",
            salvage="100",
            rate="0.5",
            life_years=5,
            decimals=2,
            rounding="HALF_EVEN",
        )
        schedule = result["schedule"]
        assert len(schedule) == 5
        for entry in schedule:
            bv = Decimal(entry["book_value_end"])
            assert bv >= Decimal("100"), f"Book value went below salvage: {bv}"
        assert schedule[4]["book_value_end"] == "100.00"
        assert "trace" in result

    def test_declining_balance_basic(self) -> None:
        """cost=100, rate=0.25, no salvage constraint, life=3."""
        result = REGISTRY.invoke(
            "accounting.depreciation_declining_balance",
            cost="100",
            salvage="0",
            rate="0.25",
            life_years=3,
            decimals=4,
            rounding="HALF_EVEN",
        )
        schedule = result["schedule"]
        assert len(schedule) == 3
        # Year 1: 100 * 0.25 = 25, book_value = 75
        assert Decimal(schedule[0]["depreciation"]) == Decimal("25.0000")
        assert Decimal(schedule[0]["book_value_end"]) == Decimal("75.0000")

    def test_declining_balance_trace(self) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_declining_balance",
            cost="500",
            salvage="50",
            rate="0.3",
            life_years=4,
            decimals=0,
            rounding="HALF_EVEN",
        )
        assert "trace" in result
        assert result["trace"]["tool"] == "accounting.depreciation_declining_balance"


class TestUnitsOfProduction:
    def test_units_production(self) -> None:
        """총 1000단위, 기간별 [100, 300, 600], cost=1100, salvage=100"""
        result = REGISTRY.invoke(
            "accounting.depreciation_units_of_production",
            cost="1100",
            salvage="100",
            total_units=1000,
            period_units=[100, 300, 600],
            decimals=0,
            rounding="HALF_EVEN",
        )
        schedule = result["schedule"]
        assert len(schedule) == 3

        # rate per unit = (1100 - 100) / 1000 = 1
        # period 1: 100 * 1 = 100, bv = 1000
        assert schedule[0]["period"] == 1
        assert Decimal(schedule[0]["depreciation"]) == Decimal("100")
        assert Decimal(schedule[0]["book_value_end"]) == Decimal("1000")

        # period 2: 300 * 1 = 300, bv = 700
        assert Decimal(schedule[1]["depreciation"]) == Decimal("300")
        assert Decimal(schedule[1]["book_value_end"]) == Decimal("700")

        # period 3: 600 * 1 = 600, bv = 100 (salvage)
        assert Decimal(schedule[2]["depreciation"]) == Decimal("600")
        assert Decimal(schedule[2]["book_value_end"]) == Decimal("100")
        assert "trace" in result

    def test_units_production_schedule_fields(self) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_units_of_production",
            cost="5000",
            salvage="500",
            total_units=9000,
            period_units=[3000, 3000, 3000],
            decimals=2,
            rounding="HALF_EVEN",
        )
        for entry in result["schedule"]:
            assert "period" in entry
            assert "units" in entry
            assert "depreciation" in entry
            assert "book_value_end" in entry
