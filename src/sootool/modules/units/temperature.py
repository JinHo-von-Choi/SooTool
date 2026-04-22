"""Temperature scale conversion tool using direct formulas."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, mul, sub
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

# Supported temperature scales
_SCALES = frozenset({"C", "F", "K", "R"})

# Absolute zero constraints (values below these are physically impossible)
_ABS_ZERO: dict[str, Decimal] = {
    "C": Decimal("-273.15"),
    "F": Decimal("-459.67"),
    "K": Decimal("0"),
    "R": Decimal("0"),
}

_KELVIN_OFFSET  = Decimal("273.15")
_RANKINE_FACTOR = Decimal("9") / Decimal("5")
_F_OFFSET       = Decimal("32")
_F_FACTOR       = Decimal("9") / Decimal("5")
_C_FACTOR       = Decimal("5") / Decimal("9")


def _to_celsius(value: Decimal, scale: str) -> Decimal:
    """Convert any supported scale to Celsius."""
    if scale == "C":
        return value
    if scale == "F":
        return mul(_C_FACTOR, sub(value, _F_OFFSET))
    if scale == "K":
        return sub(value, _KELVIN_OFFSET)
    # R → C: first R→K (divide by 9/5 = multiply by 5/9), then K→C
    k = mul(_C_FACTOR, value)
    return sub(k, _KELVIN_OFFSET)


def _from_celsius(celsius: Decimal, scale: str) -> Decimal:
    """Convert a Celsius value to the target scale."""
    if scale == "C":
        return celsius
    if scale == "F":
        return add(mul(_F_FACTOR, celsius), _F_OFFSET)
    if scale == "K":
        return add(celsius, _KELVIN_OFFSET)
    # C → R: C→K, then K→R (multiply by 9/5)
    k = add(celsius, _KELVIN_OFFSET)
    return mul(_RANKINE_FACTOR, k)


@REGISTRY.tool(
    namespace="units",
    name="temperature",
    description="Temperature conversion between Celsius, Fahrenheit, Kelvin, Rankine.",
    version="1.0.0",
)
def temperature(
    value: str,
    from_scale: str,
    to_scale: str,
) -> dict[str, Any]:
    """Convert a temperature value between C, F, K, and R scales.

    Uses direct closed-form formulas (no pint) for maximum clarity:
      C ↔ F: F = C * 9/5 + 32
      C ↔ K: K = C + 273.15
      C ↔ R: R = (C + 273.15) * 9/5

    Args:
        value:      Temperature magnitude as a Decimal string.
        from_scale: Source scale: "C" | "F" | "K" | "R".
        to_scale:   Target scale: "C" | "F" | "K" | "R".

    Returns:
        {value: str, scale: str, trace}

    Raises:
        InvalidInputError: If scale is unknown or value is below absolute zero.
    """
    trace = CalcTrace(
        tool="units.temperature",
        formula="value → Celsius → to_scale",
    )
    from_upper = from_scale.upper()
    to_upper   = to_scale.upper()

    if from_upper not in _SCALES:
        raise InvalidInputError(f"지원하지 않는 온도 단위: {from_scale!r}. 지원: C, F, K, R")
    if to_upper not in _SCALES:
        raise InvalidInputError(f"지원하지 않는 온도 단위: {to_scale!r}. 지원: C, F, K, R")

    value_d = D(value)

    abs_zero = _ABS_ZERO[from_upper]
    if value_d < abs_zero:
        raise InvalidInputError(
            f"절대영도({abs_zero} {from_upper}) 미만의 온도는 물리적으로 불가능합니다."
        )

    trace.input("value",      value)
    trace.input("from_scale", from_upper)
    trace.input("to_scale",   to_upper)

    celsius = _to_celsius(value_d, from_upper)
    result  = _from_celsius(celsius, to_upper)

    trace.step("celsius", str(celsius))
    trace.step("result",  str(result))
    trace.output({"value": str(result), "scale": to_upper})

    return {
        "value": str(result),
        "scale": to_upper,
        "trace": trace.to_dict(),
    }
