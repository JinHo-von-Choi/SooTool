"""Physical unit conversion tool backed by pint with Decimal magnitude."""
from __future__ import annotations

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.units import _UREG


class ConvertResult(TracedResult):
    magnitude: str
    unit:      str


@REGISTRY.tool(
    namespace="units",
    name="convert",
    description=(
        "pint 로 물리 단위를 변환한다. magnitude 는 Decimal 문자열, from_unit 과 to_unit 은 pint 단위 이름"
        "(meter, foot, km 등)이고 차원이 다르거나 모르는 단위는 오류이다. 결과 magnitude 는 문자열이며 "
        "1E+3 같은 지수 표기가 나올 수 있다. 섭씨·화씨는 끝자리 오차가 생기므로 units.temperature 를 쓴다."
    ),
    version="1.0.0",
)
def convert(
    magnitude: str,
    from_unit: str,
    to_unit: str,
) -> ConvertResult:
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
