from decimal import Decimal
import pytest
from sootool.core.units import Q, convert, serialize

def test_Q_creates_quantity():
    q = Q("10", "meter")
    assert q.magnitude == Decimal("10")
    assert str(q.units) == "meter"

def test_convert_length():
    q = convert(Q("1000", "meter"), "kilometer")
    assert q.magnitude == Decimal("1")

def test_convert_incompatible_raises():
    with pytest.raises(Exception):
        convert(Q("1", "meter"), "second")

def test_serialize_roundtrip():
    q = Q("2.5", "kilogram")
    data = serialize(q)
    assert data == {"magnitude": "2.5", "unit": "kilogram"}
