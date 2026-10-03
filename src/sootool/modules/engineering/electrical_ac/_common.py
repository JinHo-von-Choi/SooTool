"""Shared constants and mpmath helpers for the AC circuit tools.
"""
from __future__ import annotations

from decimal import Decimal

import mpmath

from sootool.core.cast import mpmath_to_decimal
from sootool.core.errors import InvalidInputError

_ZERO     = Decimal("0")


_ONE      = Decimal("1")


_TWO      = Decimal("2")


_MP_DPS   = 50


_OUT_DIG  = 30


def _sqrt_mp(x: Decimal) -> Decimal:
    """High-precision square root via mpmath, returned as Decimal."""
    if x < _ZERO:
        raise InvalidInputError("제곱근의 피연산자는 0 이상이어야 합니다.")
    if x == _ZERO:
        return _ZERO
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.sqrt(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _atan2_deg_mp(y: Decimal, x: Decimal) -> Decimal:
    """Four-quadrant atan2 in degrees via mpmath."""
    with mpmath.workdps(_MP_DPS):
        rad = mpmath.atan2(mpmath.mpf(str(y)), mpmath.mpf(str(x)))
        deg = rad * mpmath.mpf("180") / mpmath.pi
        return mpmath_to_decimal(deg, digits=_OUT_DIG)


def _pi_dec() -> Decimal:
    """High-precision π as Decimal."""
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.pi, digits=_OUT_DIG)
