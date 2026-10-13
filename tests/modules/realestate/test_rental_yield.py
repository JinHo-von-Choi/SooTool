"""Tests for rental yield calculator."""
from __future__ import annotations

from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest

import sootool.modules.realestate  # noqa: F401
import sootool.server  # noqa: F401, registers core.batch
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.realestate.rental_yield import realestate_rental_yield


class TestRentalYield:
    def test_rental_yield_gross_simple(self) -> None:
        """rent=50M, price=1B -> 5.00%."""
        result = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
        )
        assert result["yield_pct"] == "5.00"
        assert "trace" in result

    def test_rental_yield_net(self) -> None:
        """rent=50M, price=1B, expenses=10M -> net=(40M/1B)*100=4.00%."""
        result = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
            annual_expenses="10000000",
            yield_type="net",
        )
        assert result["yield_pct"] == "4.00"

    def test_rental_yield_gross_ignores_expenses(self) -> None:
        """Gross yield ignores annual_expenses."""
        result_no_exp = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
            yield_type="gross",
        )
        result_with_exp = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
            annual_expenses="10000000",
            yield_type="gross",
        )
        assert result_no_exp["yield_pct"] == result_with_exp["yield_pct"]

    def test_rental_yield_custom_decimals(self) -> None:
        result = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="33333333",
            property_price="1000000000",
            decimals=4,
        )
        assert len(result["yield_pct"].split(".")[1]) <= 4

    def test_rental_yield_invalid_type_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.rental_yield",
                annual_rent="50000000",
                property_price="1000000000",
                yield_type="invalid",
            )

    def test_rental_yield_zero_price_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.rental_yield",
                annual_rent="50000000",
                property_price="0",
            )

    def test_rental_yield_negative_expenses_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.rental_yield",
                annual_rent="50000000",
                property_price="1000000000",
                annual_expenses="-1",
                yield_type="net",
            )

    def test_realestate_batch_race_free(self) -> None:
        """Multiple realestate tools in batch -> deterministic results."""
        items = [
            {
                "tool": "realestate.rental_yield",
                "args": {
                    "annual_rent":    "50000000",
                    "property_price": "1000000000",
                },
                "id": "yield1",
            },
            {
                "tool": "realestate.kr_dsr",
                "args": {
                    "annual_debt_payment": "3000000",
                    "annual_income":       "10000000",
                    "year":                2026,
                },
                "id": "dsr1",
            },
        ]
        batch_result = REGISTRY.invoke(
            "core.batch",
            items=items,
            deterministic=True,
        )
        results_map = {r["id"]: r for r in batch_result["results"]}
        assert results_map["yield1"]["result"]["yield_pct"] == "5.00"
        dsr = Decimal(results_map["dsr1"]["result"]["dsr"])
        assert abs(dsr - Decimal("0.30")) < Decimal("0.0001")


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"annual_rent": "0"}, "0.00"),
        ({"annual_rent": "2", "annual_expenses": "2", "yield_type": "net"}, "0.00"),
        ({"annual_rent": "2", "annual_expenses": "3", "yield_type": "net"}, "-100.00"),
        ({"annual_rent": "1", "property_price": "1600", "decimals": 3}, "0.062"),
        ({"annual_rent": "3", "property_price": "1600", "decimals": 3}, "0.188"),
        ({"annual_rent": "15", "property_price": "1000", "decimals": 0}, "2"),
        ({"annual_rent": "1", "property_price": "1600", "decimals": 3,
          "rounding": "HALF_UP"}, "0.063"),
    ],
)
def test_rental_yield_boundaries_and_rounding(kwargs, expected):
    inputs = {"annual_rent": "1", "property_price": "1"}
    inputs.update(kwargs)
    result = REGISTRY.invoke("realestate.rental_yield", **inputs)
    assert result["yield_pct"] == expected
    assert result["trace"]["output"] == expected


@pytest.mark.parametrize("field", ["annual_rent", "property_price", "annual_expenses"])
@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "invalid", 0.1])
def test_rental_yield_invalid_numbers(field, value):
    inputs = {"annual_rent": "1", "property_price": "1", "annual_expenses": "0"}
    inputs[field] = value
    with pytest.raises(InvalidInputError):
        realestate_rental_yield(**inputs)


@pytest.mark.parametrize("decimals", [-1, True, 1.5, "2", None])
def test_rental_yield_invalid_decimals(decimals):
    with pytest.raises(InvalidInputError):
        realestate_rental_yield("1", "1", decimals=decimals)


@pytest.mark.parametrize("price", ["0", "-0", "-1"])
def test_rental_yield_nonpositive_price(price):
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("realestate.rental_yield", annual_rent="1", property_price=price)


def test_rental_yield_precision_and_context_isolation():
    rent = "1." + "0" * 59 + "3"
    expenses = "1." + "0" * 59 + "1"
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        context.Emax = 9
        context.Emin = -9
        context.clear_flags()
        result = realestate_rental_yield(
            rent, "3", expenses, yield_type="net", decimals=60,
        )
        assert context.prec == 6
        assert context.rounding == ROUND_UP
        assert context.traps[Inexact]
        assert context.Emax == 9 and context.Emin == -9
        assert not any(context.flags.values())
    assert Decimal(result["yield_pct"]) == Decimal("6.7e-59")
    assert Decimal(result["yield_pct"]).as_tuple().exponent == -60
    assert result["trace"]["output"] == result["yield_pct"]


def test_rental_yield_out_of_decimal_range():
    with pytest.raises(InvalidInputError, match="Decimal"):
        realestate_rental_yield("1e999999", "1")


@pytest.mark.parametrize("kwargs", [{"annual_rent": "-1"}, {"rounding": "invalid"}])
def test_rental_yield_invalid_options(kwargs):
    inputs = {"annual_rent": "1", "property_price": "1"}
    inputs.update(kwargs)
    with pytest.raises(InvalidInputError):
        realestate_rental_yield(**inputs)


def test_rental_yield_preserves_digits_above_rounding_tie():
    result = realestate_rental_yield("0.025" + "0" * 60 + "1", "1", decimals=0)
    assert result["yield_pct"] == "3"
