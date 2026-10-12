from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest

from sootool.core.errors import InvalidInputError
from sootool.core.rounding import RoundingPolicy, apply, truncate_to_unit


def test_half_even_banker_rounding():
    assert apply(Decimal("2.5"), 0, RoundingPolicy.HALF_EVEN) == Decimal("2")
    assert apply(Decimal("3.5"), 0, RoundingPolicy.HALF_EVEN) == Decimal("4")

def test_half_up_traditional():
    assert apply(Decimal("2.5"), 0, RoundingPolicy.HALF_UP) == Decimal("3")

def test_down_truncate():
    assert apply(Decimal("2.9"), 0, RoundingPolicy.DOWN) == Decimal("2")
    assert apply(Decimal("-2.9"), 0, RoundingPolicy.DOWN) == Decimal("-2")

def test_up_away_from_zero():
    assert apply(Decimal("2.1"), 0, RoundingPolicy.UP) == Decimal("3")
    assert apply(Decimal("-2.1"), 0, RoundingPolicy.UP) == Decimal("-3")

def test_floor_toward_neg_inf():
    assert apply(Decimal("-2.1"), 0, RoundingPolicy.FLOOR) == Decimal("-3")

def test_ceil_toward_pos_inf():
    assert apply(Decimal("2.1"), 0, RoundingPolicy.CEIL) == Decimal("3")

def test_decimals_parameter():
    assert apply(Decimal("1.23456"), 2, RoundingPolicy.HALF_EVEN) == Decimal("1.23")


@pytest.mark.parametrize(("value", "unit", "expected"), [
    ("0", "10", "0"),
    ("9.999", "10", "0"),
    ("10", "10", "10"),
    ("10.001", "10", "10"),
    ("-9.999", "10", "0"),
    ("-10.001", "10", "-10"),
    ("1.24", "0.25", "1.00"),
    ("-1.24", "0.25", "-1.00"),
    ("11", "3", "9"),
])
def test_truncate_to_unit_boundaries(value, unit, expected):
    assert truncate_to_unit(Decimal(value), Decimal(unit)) == Decimal(expected)


@pytest.mark.parametrize("unit", ["0", "-0", "-10", "NaN", "sNaN", "Infinity", "-Infinity"])
def test_truncate_to_unit_invalid_unit(unit):
    with pytest.raises(InvalidInputError, match="unit"):
        truncate_to_unit(Decimal("100"), Decimal(unit))


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_truncate_to_unit_nonfinite_value(value):
    with pytest.raises(InvalidInputError, match="value"):
        truncate_to_unit(Decimal(value), Decimal("10"))


@pytest.mark.parametrize(("value", "unit", "expected"), [
    ("9." + "9" * 60, "10", "0"),
    ("-9." + "9" * 60, "10", "0"),
    ("123456789012345678901234567890.999", "0.01", "123456789012345678901234567890.99"),
    ("0.000000000000000000000000000001239", "0.00000000000000000000000000000001",
     "0.00000000000000000000000000000123"),
])
@pytest.mark.parametrize("precision", [3, 50])
@pytest.mark.parametrize("trap_inexact", [False, True])
def test_truncate_to_unit_precision_independent_of_context(value, unit, expected, precision, trap_inexact):
    with localcontext() as context:
        context.prec = precision
        context.rounding = ROUND_UP
        context.traps[Inexact] = trap_inexact
        context.clear_flags()
        assert truncate_to_unit(Decimal(value), Decimal(unit)) == Decimal(expected)
        assert context.prec == precision
        assert context.rounding == ROUND_UP
        assert context.traps[Inexact] == trap_inexact
        assert not context.flags[Inexact]


@pytest.mark.parametrize(("value", "unit", "expected"), [
    ("123.456000", "10", "120"),
    ("1.24", "0.25", "1.00"),
    ("1234.56", "1E+3", "1E+3"),
    ("-0.1", "10", "-0"),
])
def test_truncate_to_unit_preserves_unit_scale(value, unit, expected):
    assert str(truncate_to_unit(Decimal(value), Decimal(unit))) == expected
