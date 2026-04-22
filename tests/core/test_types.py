from decimal import Decimal
import pytest
from sootool.core.types import Money, Percent
from sootool.core.errors import SooToolError, InvalidInputError

def test_money_decimal_string_only():
    m = Money(amount="100.50", currency="KRW")
    assert m.amount == Decimal("100.50")
    assert m.currency == "KRW"

def test_money_rejects_float():
    with pytest.raises(Exception):
        Money(amount=100.5, currency="KRW")

def test_money_rejects_int():
    with pytest.raises(Exception):
        Money(amount=100, currency="KRW")

def test_percent_normalizes():
    p = Percent(value="5")
    assert p.value == Decimal("5")
    assert p.as_fraction() == Decimal("0.05")

def test_percent_rejects_float():
    with pytest.raises(Exception):
        Percent(value=5.0)

def test_percent_rejects_int():
    with pytest.raises(Exception):
        Percent(value=5)

def test_error_hierarchy():
    assert issubclass(InvalidInputError, SooToolError)
