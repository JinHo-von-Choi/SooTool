"""CAGR precision and boundary regressions."""
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext

import pytest

from sootool.core.errors import InvalidInputError
from sootool.modules.finance.metrics import cagr


@pytest.mark.parametrize("periods", [1, 2, 3])
@pytest.mark.parametrize(
    ("ending_value", "expected"),
    [("0", "-1.000000"), ("1", "0.000000")],
)
def test_zero_and_unchanged_values_with_low_precision(periods, ending_value, expected):
    with localcontext() as context:
        context.prec = 3
        result = cagr("1", ending_value, periods)
    assert Decimal(result["cagr"]) == Decimal(expected)
    assert result["trace"]["output"] == result["cagr"]


@pytest.mark.parametrize(
    ("ending_value", "expected"),
    [
        ("1." + "0" * 59 + "2", "0." + "0" * 59 + "1"),
        ("0." + "9" * 59 + "8", "-0." + "0" * 59 + "1"),
    ],
)
def test_multi_period_preserves_tiny_growth_and_loss(ending_value, expected):
    result = cagr("1", ending_value, 2, decimals=60)
    assert Decimal(result["cagr"]) == Decimal(expected)
    assert result["trace"]["output"] == result["cagr"]


def test_large_values_preserve_small_single_period_change():
    beginning = "1" + "0" * 60
    result = cagr(beginning, beginning + ".01", 1, decimals=62)
    assert Decimal(result["cagr"]) == Decimal("1e-62")


def test_large_growth_has_room_for_integer_and_fractional_digits():
    result = cagr("1", "1e80", 2)
    assert result["cagr"] == "9" * 40 + ".000000"


def test_precision_is_independent_of_caller_context():
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        result = cagr("1", "2", 2, decimals=60)
        assert context.prec == 6
        assert context.rounding == ROUND_DOWN
        assert context.traps[Inexact] is True
    assert result["cagr"] == (
        "0.414213562373095048801688724209698078569671875376948073176680"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"beginning_value": "0"},
        {"ending_value": "-1"},
        {"ending_value": "sNaN"},
        {"beginning_value": "Infinity"},
        {"periods": 0},
        {"periods": True},
        {"decimals": -1},
        {"rounding": "INVALID"},
    ],
)
def test_invalid_inputs_raise_domain_error_with_low_precision(kwargs):
    arguments = {"beginning_value": "1", "ending_value": "2", "periods": 2}
    arguments.update(kwargs)
    with localcontext() as context:
        context.prec = 3
        with pytest.raises(InvalidInputError):
            cagr(**arguments)
