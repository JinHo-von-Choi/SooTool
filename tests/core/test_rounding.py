from decimal import Decimal

from sootool.core.rounding import RoundingPolicy, apply


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
