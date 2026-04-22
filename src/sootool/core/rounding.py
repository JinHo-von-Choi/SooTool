from __future__ import annotations

from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)
from enum import StrEnum


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
