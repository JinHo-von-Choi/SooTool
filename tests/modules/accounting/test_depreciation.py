"""Tests for accounting depreciation tools."""
from __future__ import annotations

from decimal import ROUND_UP, Decimal, localcontext

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.accounting.depreciation import (
    depreciation_declining_balance,
    depreciation_straight_line,
    depreciation_units_of_production,
)


class TestStraightLine:
    @pytest.mark.parametrize("rounding", ["HALF_EVEN", "HALF_UP", "DOWN", "UP", "FLOOR", "CEIL"])
    @pytest.mark.parametrize("cost,salvage,life", [
        ("2", "0", 4), ("10", "1.5", 3), ("0", "0", 1), ("1.5", "1.5", 2),
    ])
    def test_rounding_preserves_salvage_and_expense_conservation(
        self, rounding: str, cost: str, salvage: str, life: int,
    ) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_straight_line",
            cost=cost, salvage=salvage, life_years=life, rounding=rounding,
        )
        previous = Decimal(cost)
        total = Decimal("0")
        assert len(result["schedule"]) == life
        for row in result["schedule"]:
            expense = Decimal(row["depreciation"])
            book_value = Decimal(row["book_value_end"])
            assert expense >= 0
            assert previous - expense == book_value
            assert book_value >= Decimal(salvage)
            total += expense
            previous = book_value
        assert previous == Decimal(salvage)
        assert total == Decimal(cost) - Decimal(salvage)

    @pytest.mark.parametrize("overrides", [
        {"cost": "-1"}, {"salvage": "-1"}, {"salvage": "11"},
        {"cost": "NaN"}, {"cost": "sNaN"}, {"cost": "Infinity"},
        {"salvage": "NaN"}, {"salvage": "-Infinity"}, {"cost": "invalid"},
        {"cost": 0.1}, {"life_years": 0}, {"life_years": -1},
        {"life_years": True}, {"life_years": 1.5}, {"life_years": "2"},
        {"decimals": -1}, {"decimals": True}, {"decimals": 1.5},
        {"decimals": "2"}, {"rounding": "INVALID"},
    ])
    def test_invalid_inputs(self, overrides: dict) -> None:
        kwargs = dict(cost="10", salvage="1", life_years=3)
        kwargs.update(overrides)
        with pytest.raises(InvalidInputError):
            depreciation_straight_line(**kwargs)

    @pytest.mark.parametrize("cost", [
        "1.000000000000000000000000000003",
        "1." + "0" * 59 + "3",
    ])
    def test_small_depreciable_base_ignores_caller_context(self, cost: str) -> None:
        decimals = len(cost.split(".")[1])
        expected_expense = Decimal("0." + "0" * (decimals - 1) + "1")
        with localcontext() as context:
            context.prec = 6
            context.rounding = ROUND_UP
            result = depreciation_straight_line(cost, "1", 3, decimals=decimals)
            assert Decimal(result["annual_expense"]) == expected_expense
            assert [Decimal(row["depreciation"]) for row in result["schedule"]] == [expected_expense] * 3
            assert Decimal(result["schedule"][-1]["book_value_end"]) == 1
            assert context.prec == 6
            assert context.rounding == ROUND_UP

    @pytest.mark.parametrize("rounding,expected", [("HALF_EVEN", "0.12"), ("HALF_UP", "0.13")])
    def test_annual_rounding_tie(self, rounding: str, expected: str) -> None:
        result = depreciation_straight_line("1", "0", 8, decimals=2, rounding=rounding)
        assert result["annual_expense"] == expected
        assert result["schedule"][0]["depreciation"] == expected
        assert Decimal(result["schedule"][-1]["book_value_end"]) == 0

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
    @pytest.mark.parametrize("rounding", ["HALF_EVEN", "HALF_UP", "DOWN", "UP", "FLOOR", "CEIL"])
    def test_fractional_salvage_preserves_expense_conservation(self, rounding: str) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_declining_balance",
            cost="10", salvage="1.5", rate="0.9", life_years=3, rounding=rounding,
        )
        previous = Decimal("10")
        for row in result["schedule"]:
            assert Decimal(row["book_value_start"]) == previous
            expense = Decimal(row["depreciation"])
            book_value = Decimal(row["book_value_end"])
            assert previous - expense == book_value
            assert expense >= 0
            assert book_value == Decimal("1.5")
            previous = book_value
        assert [Decimal(row["depreciation"]) for row in result["schedule"]] == [
            Decimal("8.5"), Decimal("0"), Decimal("0"),
        ]

    @pytest.mark.parametrize("cost,salvage", [("0", "0"), ("1.5", "1.5")])
    def test_no_depreciable_base(self, cost: str, salvage: str) -> None:
        result = depreciation_declining_balance(cost, salvage, "0.5", 2)
        assert len(result["schedule"]) == 2
        for row in result["schedule"]:
            assert Decimal(row["depreciation"]) == 0
            assert Decimal(row["book_value_start"]) == Decimal(cost)
            assert Decimal(row["book_value_end"]) == Decimal(cost)

    def test_precision_independent_of_caller_context(self) -> None:
        cost = "0.300000000000000000000000000004"
        expected = [
            ("0.150000000000000000000000000002", "0.150000000000000000000000000002"),
            ("0.075000000000000000000000000001", "0.075000000000000000000000000001"),
        ]
        with localcontext() as ctx:
            ctx.prec = 6
            ctx.rounding = ROUND_UP
            result = depreciation_declining_balance(cost, "0", "0.5", 2, decimals=30)
            assert ctx.prec == 6
            assert ctx.rounding == ROUND_UP
        assert [(row["depreciation"], row["book_value_end"]) for row in result["schedule"]] == expected

    @pytest.mark.parametrize("overrides", [
        {"cost": "-1"}, {"salvage": "-1"}, {"salvage": "11"},
        {"cost": "NaN"}, {"cost": "sNaN"}, {"salvage": "Infinity"},
        {"rate": "NaN"}, {"rate": "sNaN"}, {"rate": "Infinity"},
        {"cost": "invalid"}, {"rate": "invalid"},
        {"rate": "0"}, {"rate": "1"}, {"rate": "-0.1"}, {"rate": "1.1"},
        {"life_years": 0}, {"life_years": -1}, {"life_years": 1.5}, {"life_years": True},
        {"decimals": -1}, {"decimals": 1.5}, {"decimals": True}, {"rounding": "INVALID"},
    ])
    def test_invalid_inputs(self, overrides: dict) -> None:
        kwargs = dict(cost="10", salvage="1", rate="0.5", life_years=2)
        kwargs.update(overrides)
        with pytest.raises(InvalidInputError):
            depreciation_declining_balance(**kwargs)

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
    def test_independent_of_caller_decimal_context(self) -> None:
        with localcontext() as context:
            context.prec = 6
            context.rounding = ROUND_UP
            result = depreciation_units_of_production(
                "0.300000000000000000000000000003", "0", 3,
                [0, 1, 1, 1, 1], decimals=30,
            )
            assert context.prec == 6
            assert context.rounding == ROUND_UP

        assert [Decimal(row["depreciation"]) for row in result["schedule"]] == [
            Decimal("0"), *[Decimal("0.100000000000000000000000000001")] * 3,
            Decimal("0"),
        ]
        assert Decimal(result["schedule"][-1]["book_value_end"]) == 0

    def test_large_cost_preserves_small_depreciable_base(self) -> None:
        result = depreciation_units_of_production(
            "1000000000000000000000000000000000000000000000000000000000000.03",
            "1000000000000000000000000000000000000000000000000000000000000",
            3, [0, 1, 1, 1, 1], decimals=2,
        )
        assert [Decimal(row["depreciation"]) for row in result["schedule"]] == [
            Decimal("0"), Decimal("0.01"), Decimal("0.01"), Decimal("0.01"), Decimal("0"),
        ]
        assert Decimal(result["schedule"][-1]["book_value_end"]) == Decimal(
            "1000000000000000000000000000000000000000000000000000000000000"
        )

    @pytest.mark.parametrize("overrides", [
        {"cost": "sNaN"}, {"salvage": "NaN"}, {"salvage": "-Infinity"},
        {"cost": 0.1}, {"period_units": None}, {"period_units": (1,)},
        {"decimals": True},
    ])
    def test_additional_invalid_inputs(self, overrides: dict) -> None:
        kwargs = dict(cost="10", salvage="1", total_units=10, period_units=[1])
        kwargs.update(overrides)
        with pytest.raises(InvalidInputError):
            depreciation_units_of_production(**kwargs)

    @pytest.mark.parametrize("rounding", ["HALF_EVEN", "HALF_UP", "DOWN", "UP", "FLOOR", "CEIL"])
    def test_fractional_salvage_caps_expense_exactly(self, rounding: str) -> None:
        result = REGISTRY.invoke(
            "accounting.depreciation_units_of_production",
            cost="10", salvage="1.5", total_units=10,
            period_units=[100, 1, 0], decimals=0, rounding=rounding,
        )
        schedule = result["schedule"]
        assert [Decimal(row["depreciation"]) for row in schedule] == [
            Decimal("8.5"), Decimal("0"), Decimal("0"),
        ]
        assert all(Decimal(row["book_value_end"]) == Decimal("1.5") for row in schedule)

    @pytest.mark.parametrize("cost,salvage", [("0", "0"), ("1.5", "1.5")])
    def test_no_depreciable_base(self, cost: str, salvage: str) -> None:
        result = depreciation_units_of_production(cost, salvage, 1, [0, 1, 2])
        assert all(Decimal(row["depreciation"]) == 0 for row in result["schedule"])
        assert all(Decimal(row["book_value_end"]) == Decimal(cost) for row in result["schedule"])

    def test_zero_production_and_empty_schedule(self) -> None:
        assert depreciation_units_of_production("10", "1", 10, [])["schedule"] == []
        row = depreciation_units_of_production("10", "1", 10, [0])["schedule"][0]
        assert Decimal(row["depreciation"]) == 0
        assert Decimal(row["book_value_end"]) == 10

    def test_decimal_precision_and_conservation(self) -> None:
        cost = "0.300000000000000000000000000003"
        result = REGISTRY.invoke(
            "accounting.depreciation_units_of_production",
            cost=cost, salvage="0", total_units=3,
            period_units=[0, 1, 1, 1], decimals=30,
        )
        schedule = result["schedule"]
        assert [row["depreciation"] for row in schedule[1:]] == [
            "0.100000000000000000000000000001",
        ] * 3
        previous = Decimal(cost)
        for row in schedule:
            expense = Decimal(row["depreciation"])
            book_value = Decimal(row["book_value_end"])
            assert previous - expense == book_value
            assert expense >= 0 and book_value >= 0
            previous = book_value
        assert previous == 0

    @pytest.mark.parametrize("overrides", [
        {"cost": "-1"}, {"salvage": "-1"}, {"salvage": "11"},
        {"cost": "NaN"}, {"salvage": "Infinity"}, {"cost": "not-a-number"},
        {"total_units": 0}, {"total_units": -1}, {"total_units": 1.5},
        {"total_units": True}, {"period_units": [-1]}, {"period_units": [1, -1]},
        {"period_units": [1.5]}, {"period_units": [True]},
        {"decimals": -1}, {"decimals": 1.5}, {"rounding": "INVALID"},
    ])
    def test_invalid_inputs(self, overrides: dict) -> None:
        kwargs = dict(cost="10", salvage="1", total_units=10, period_units=[1])
        kwargs.update(overrides)
        with pytest.raises(InvalidInputError):
            depreciation_units_of_production(**kwargs)

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
