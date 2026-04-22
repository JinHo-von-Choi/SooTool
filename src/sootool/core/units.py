from __future__ import annotations
from decimal import Decimal
from typing import TypedDict
import threading
import pint

_UREG      = pint.UnitRegistry(non_int_type=Decimal)
_UREG_LOCK = threading.RLock()
Quantity   = _UREG.Quantity


class SerializedQuantity(TypedDict):
    magnitude: str
    unit:      str


def Q(magnitude: "str | Decimal | int", unit: str) -> Quantity:
    """Create a Quantity with a Decimal magnitude."""
    value = Decimal(magnitude) if not isinstance(magnitude, Decimal) else magnitude
    return _UREG.Quantity(value, unit)


def convert(q: Quantity, target_unit: str) -> Quantity:
    """Convert a Quantity to a different unit (read-only, lock-free)."""
    return q.to(target_unit)


def serialize(q: Quantity) -> SerializedQuantity:
    """Serialize a Quantity to a plain dict with string magnitude."""
    return {"magnitude": str(q.magnitude), "unit": str(q.units)}
