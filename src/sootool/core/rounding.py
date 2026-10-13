from __future__ import annotations

from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Context,
    Decimal,
    localcontext,
)
from enum import StrEnum

from sootool.core.errors import InvalidInputError


class RoundingPolicy(StrEnum):
    HALF_EVEN = "HALF_EVEN"
    HALF_UP   = "HALF_UP"
    DOWN      = "DOWN"
    UP        = "UP"
    FLOOR     = "FLOOR"
    CEIL      = "CEIL"


_MAP = {
    RoundingPolicy.HALF_EVEN: ROUND_HALF_EVEN,
    RoundingPolicy.HALF_UP:   ROUND_HALF_UP,
    RoundingPolicy.DOWN:      ROUND_DOWN,
    RoundingPolicy.UP:        ROUND_UP,
    RoundingPolicy.FLOOR:     ROUND_FLOOR,
    RoundingPolicy.CEIL:      ROUND_CEILING,
}


def apply(value: Decimal, decimals: int, policy: RoundingPolicy) -> Decimal:
    if decimals < 0:
        raise ValueError("decimals는 0 이상")
    quant = Decimal(10) ** -decimals if decimals > 0 else Decimal("1")
    return value.quantize(quant, rounding=_MAP[policy])


def truncate_to_unit(value: Decimal, unit: Decimal) -> Decimal:
    """유한한 value를 양수 unit의 배수로 0 방향 절사한다.

    호출자의 Decimal 정밀도와 관계없이 단위 미만의 나머지를 정확히 버린다.
    unit=10 이면 10원 미만, unit=1000 이면 천원 미만 끝수를 버린다.
    """
    if not value.is_finite():
        raise InvalidInputError("value는 유한한 숫자여야 합니다.")
    if not unit.is_finite() or unit <= 0:
        raise InvalidInputError("unit는 유한한 양수여야 합니다.")

    highest_digit = max(value.adjusted(), unit.adjusted())
    lowest_digit = min(int(value.as_tuple().exponent), int(unit.as_tuple().exponent))
    precision = max(1, highest_digit - lowest_digit + 2)
    with localcontext(Context(prec=precision)):
        # Remainder avoids rounding a quotient across an integer boundary.
        return (value - value % unit).quantize(unit).copy_sign(value)


def round_to_unit(value: Decimal, unit: Decimal, policy: RoundingPolicy) -> Decimal:
    """Round a finite value to a positive unit's multiple, preserving unit scale.

    Supports arbitrary increments such as 0.25 or 3, independently of the
    caller's Decimal precision, rounding mode, and traps.
    """
    if not value.is_finite():
        raise InvalidInputError("value는 유한한 숫자여야 합니다.")
    if not unit.is_finite() or unit <= 0:
        raise InvalidInputError("unit는 유한한 양수여야 합니다.")

    highest_digit = max(value.adjusted(), unit.adjusted())
    lowest_digit = min(int(value.as_tuple().exponent), int(unit.as_tuple().exponent))
    # Reserve coefficient digits to distinguish quotients near half-unit ties,
    # as well as a carry digit for the rounded multiple and final multiplication.
    precision = max(1, highest_digit - lowest_digit + len(unit.as_tuple().digits) + 3)
    with localcontext(Context(prec=precision)):
        multiple = (value / unit).to_integral_value(rounding=_MAP[policy])
        return (multiple * unit).quantize(unit)
