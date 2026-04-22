"""Physical unit conversion tool backed by pint with Decimal magnitude."""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.units import _UREG


@REGISTRY.tool(
    namespace="units",
    name="convert",
    description="Physical unit conversion using pint (Decimal precision). E.g. meter → feet.",
    version="1.0.0",
)
def convert(
    magnitude: str,
    from_unit: str,
    to_unit: str,
) -> dict[str, Any]:
    """Convert a physical quantity from one unit to another.

    Uses the shared pint UnitRegistry (_UREG) with Decimal non-int type for
    lossless arithmetic.

    Args:
        magnitude: Numeric magnitude as a Decimal string (e.g. "1").
        from_unit: Source unit string understood by pint (e.g. "meter").
        to_unit:   Target unit string understood by pint (e.g. "foot").

    Returns:
        {magnitude: str, unit: str, trace}

    Raises:
        InvalidInputError: If units are dimensionally incompatible or unknown.
    """
    trace = CalcTrace(
        tool="units.convert",
        formula="quantity = magnitude [from_unit]; result = quantity.to(to_unit)",
    )
    value = D(magnitude)

    trace.input("magnitude", magnitude)
    trace.input("from_unit", from_unit)
    trace.input("to_unit",   to_unit)

    try:
        quantity = _UREG.Quantity(value, from_unit)
        converted = quantity.to(to_unit)
    except Exception as exc:
        raise InvalidInputError(
            f"단위 변환 실패: {from_unit!r} → {to_unit!r}: {exc}"
        ) from exc

    result_magnitude = str(converted.magnitude)
    result_unit      = str(converted.units)

    trace.step("converted_magnitude", result_magnitude)
    trace.step("converted_unit",      result_unit)
    trace.output({"magnitude": result_magnitude, "unit": result_unit})

    return {
        "magnitude": result_magnitude,
        "unit":      result_unit,
        "trace":     trace.to_dict(),
    }
