"""SI prefix conversion tool using Decimal arithmetic."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

# SI prefix exponents (base-10 powers).
# Keys are lowercase prefix names; values are the integer exponent.
SI_PREFIXES: dict[str, int] = {
    "yocto": -24,
    "zepto": -21,
    "atto":  -18,
    "femto": -15,
    "pico":  -12,
    "nano":   -9,
    "micro":  -6,
    "milli":  -3,
    "centi":  -2,
    "deci":   -1,
    "":        0,   # base (no prefix)
    "base":    0,
    "deca":    1,
    "hecto":   2,
    "kilo":    3,
    "mega":    6,
    "giga":    9,
    "tera":   12,
    "peta":   15,
    "exa":    18,
    "zetta":  21,
    "yotta":  24,
}


def _resolve_prefix(prefix: str) -> int:
    """Return the exponent for a named prefix (case-insensitive)."""
    key = prefix.strip().lower()
    if key not in SI_PREFIXES:
        raise InvalidInputError(
            f"알 수 없는 SI 접두사: {prefix!r}. "
            f"지원 목록: {', '.join(sorted(SI_PREFIXES.keys()))}"
        )
    return SI_PREFIXES[key]


@REGISTRY.tool(
    namespace="engineering",
    name="si_prefix_convert",
    description="Convert a value between SI prefixes (e.g. mega → milli). Uses Decimal × 10^(from_exp - to_exp).",
    version="1.0.0",
)
def si_prefix_convert(
    value:       str,
    from_prefix: str,
    to_prefix:   str,
) -> dict[str, Any]:
    """Convert a numeric value between SI prefix scales.

    Formula: result = value × 10^(from_exponent − to_exponent)

    Examples:
      1 mega → milli: 1 × 10^(6 − (−3)) = 1 × 10^9 = 1_000_000_000
      5 kilo → kilo:  5 × 10^(3 − 3)    = 5 × 10^0 = 5 (identity)

    Args:
        value:       Numeric magnitude as a Decimal string.
        from_prefix: Source SI prefix name (e.g. "mega", "kilo", "milli").
        to_prefix:   Target SI prefix name.

    Returns:
        {value: str, trace}

    Raises:
        InvalidInputError: If a prefix name is not recognised.
    """
    trace = CalcTrace(
        tool="engineering.si_prefix_convert",
        formula="result = value × 10^(from_exp − to_exp)",
    )

    value_d    = D(value)
    from_exp   = _resolve_prefix(from_prefix)
    to_exp     = _resolve_prefix(to_prefix)
    exp_delta  = from_exp - to_exp
    scale      = Decimal(10) ** exp_delta
    result     = mul(value_d, scale)

    trace.input("value",       value)
    trace.input("from_prefix", from_prefix.lower())
    trace.input("to_prefix",   to_prefix.lower())
    trace.step("from_exp",     from_exp)
    trace.step("to_exp",       to_exp)
    trace.step("exp_delta",    exp_delta)
    trace.step("scale",        str(scale))
    trace.step("result",       str(result))
    trace.output(str(result))

    return {
        "value": str(result),
        "trace": trace.to_dict(),
    }
