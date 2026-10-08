"""Tests for accounting.break_even."""
from __future__ import annotations

from decimal import ROUND_UP, Decimal, localcontext

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    inputs = {"fixed_costs": "1000", "unit_price": "25", "unit_variable_cost": "15"}
    inputs.update(kwargs)
    return REGISTRY.invoke("accounting.break_even", **inputs)


def test_standard_break_even():
    result = call()
    assert result["break_even_units"] == "100.0000"
    assert result["trace"]["tool"] == "accounting.break_even"
    assert result["trace"]["output"] == result["break_even_units"]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"fixed_costs": "0"}, "0.0000"),
        ({"unit_variable_cost": "0"}, "40.0000"),
        ({"fixed_costs": "1", "unit_price": "3", "unit_variable_cost": "0"}, "0.3333"),
    ],
)
def test_boundaries_and_fractional_units(kwargs, expected):
    assert call(**kwargs)["break_even_units"] == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fixed_costs": "-0.01"},
        {"unit_price": "0"},
        {"unit_price": "-1"},
        {"unit_variable_cost": "-0.01"},
        {"unit_variable_cost": "25"},
        {"unit_variable_cost": "26"},
        {"fixed_costs": "0", "unit_variable_cost": "25"},
        {"decimals": -1},
        {"decimals": 1.5},
        {"decimals": True},
    ],
)
def test_invalid_inputs(kwargs):
    with pytest.raises(InvalidInputError):
        call(**kwargs)


@pytest.mark.parametrize("field", ["fixed_costs", "unit_price", "unit_variable_cost"])
@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "invalid", 0.1])
def test_invalid_numbers(field, value):
    with pytest.raises(InvalidInputError):
        call(**{field: value})


@pytest.mark.parametrize(("fixed_costs", "expected"), [("1", "0.062"), ("3", "0.188")])
def test_half_even_precision_boundary(fixed_costs, expected):
    assert call(
        fixed_costs=fixed_costs, unit_price="16", unit_variable_cost="0", decimals=3,
    )["break_even_units"] == expected


def test_decimal_precision_preserves_small_contribution_margin():
    result = call(
        fixed_costs="0.000000000000000003",
        unit_price="1.000000000000000003",
        unit_variable_cost="1.000000000000000001",
        decimals=18,
    )
    assert result["break_even_units"] == "1.500000000000000000"
    assert Decimal(result["break_even_units"]) * Decimal("0.000000000000000002") == Decimal("0.000000000000000003")


def test_zero_decimal_rounding():
    assert call(fixed_costs="15", decimals=0)["break_even_units"] == "2"


def test_calculation_is_independent_of_caller_decimal_context():
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_UP
        result = call(
            fixed_costs="0.000000000000000003",
            unit_price="1.000000000000000003",
            unit_variable_cost="1.000000000000000001",
            decimals=18,
        )
        assert result["break_even_units"] == "1.500000000000000000"
        assert context.prec == 6
        assert context.rounding == ROUND_UP


def test_unsupported_output_precision_raises_domain_error():
    with pytest.raises(InvalidInputError, match="Decimal"):
        call(decimals=100)
