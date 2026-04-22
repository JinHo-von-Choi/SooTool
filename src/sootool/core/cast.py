"""
core/cast.py — Boundary casting between Decimal, float64, mpmath, and pint Quantity.

All cross-type conversions in SooTool must go through this module.
No module may call float() on a Decimal or cast mpf directly outside this file.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import mpmath

from sootool.core.units import _UREG

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# float64 has 15–17 significant decimal digits of precision.
_FLOAT64_MAX_SAFE_DIGITS = 15


def decimal_to_float64(x: Decimal) -> float:
    """
    Convert a Decimal to a Python float (float64).

    Logs a WARNING when the Decimal has more significant digits than float64
    can represent exactly (> 15 significant decimal digits).
    """
    sign, digits, exponent = x.as_tuple()
    if len(digits) > _FLOAT64_MAX_SAFE_DIGITS:
        log.warning(
            "decimal_to_float64: precision loss possible — "
            "Decimal has %d significant digits, float64 supports ~%d. value=%s",
            len(digits),
            _FLOAT64_MAX_SAFE_DIGITS,
            x,
        )
    return float(x)


def float64_to_decimal_str(x: float, digits: int = 15) -> str:
    """
    Convert a float64 to a clean decimal string without floating-point noise.

    Uses mpmath at the requested precision so that 0.1 -> "0.1" rather than
    "0.1000000000000000056" which is what str(Decimal(0.1)) would produce.

    The result is stripped of trailing zeros after the decimal point.
    """
    mp_val = mpmath.mpf(x)
    # nstr produces a minimal string representation at the given number of digits
    raw: str = str(mpmath.nstr(mp_val, digits, strip_zeros=True))
    # Remove trailing dot and ".0" suffix (e.g. "42." or "42.0" -> "42")
    if "." in raw:
        raw = raw.rstrip("0").rstrip(".")
    return raw


def mpmath_to_decimal(x: mpmath.mpf, digits: int = 50) -> Decimal:
    """
    Convert an mpmath.mpf to a Decimal with the given number of significant digits.

    Uses mpmath.nstr to produce a high-precision decimal string, then parses
    it into Decimal to avoid any intermediate float64 representation.
    """
    raw = mpmath.nstr(x, digits, strip_zeros=False)
    return Decimal(raw)


def quantity_to_snapshot(q: Any) -> dict[str, str]:
    """
    Serialize a pint Quantity to a JSON-safe dict.

    Returns {"magnitude": str, "unit": str}.
    The magnitude is converted to string to preserve Decimal precision.
    """
    return {
        "magnitude": str(q.magnitude),
        "unit":      str(q.units),
    }


def snapshot_to_quantity(d: dict[str, str]) -> Any:
    """
    Reconstruct a pint Quantity from a snapshot dict.

    Uses the singleton _UREG from core.units so the result is compatible
    with all other Quantity objects produced by this package.
    """
    magnitude = Decimal(d["magnitude"])
    unit      = d["unit"]
    return _UREG.Quantity(magnitude, unit)
