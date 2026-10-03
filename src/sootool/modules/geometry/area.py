"""Geometry area tools: circle, triangle, rectangle, polygon (shoelace)."""
from __future__ import annotations

from decimal import Decimal

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_MPMATH_DPS = 50  # decimal places for mpmath calculations


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name} 은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


class AreaCircleResult(TracedResult):
    area: str


@REGISTRY.tool(
    namespace="geometry",
    name="area_circle",
    description=(
        "원의 넓이 π * r² 를 계산한다. "
        "radius 는 0 이상 Decimal 문자열이며 단위는 자유(결과는 그 단위의 제곱). π 는 mpmath 50자리로 계산하고 유효숫자 30자리 문자열로 반환한다. "
        "지름을 radius 로 넣으면 4배 큰 값이 나오므로 반지름을 넣는다."
    ),
    version="1.0.0",
)
def area_circle(radius: str) -> AreaCircleResult:
    """Compute the area of a circle with the given radius.

    Uses mpmath.pi for high-precision computation.

    Args:
        radius: Radius as Decimal string (non-negative).

    Returns:
        {area: str, trace}
    """
    trace = CalcTrace(tool="geometry.area_circle", formula="π * r²")
    trace.input("radius", radius)

    r = _parse_decimal(radius, "radius")
    if r < 0:
        raise DomainConstraintError(f"radius 는 음수가 될 수 없습니다: {r}")

    with mpmath.workdps(_MPMATH_DPS):
        r_mp  = mpmath.mpf(str(r))
        area  = mpmath.pi * r_mp * r_mp
        # Convert to Decimal string with enough significant digits
        area_str = mpmath.nstr(area, 30, strip_zeros=False)

    result = D(area_str)

    trace.step("pi", str(mpmath.nstr(mpmath.pi, 20)))
    trace.step("area", str(result))
    trace.output({"area": str(result)})

    return {"area": str(result), "trace": trace.to_dict()}


class AreaTriangleResult(TracedResult):
    area: str


@REGISTRY.tool(
    namespace="geometry",
    name="area_triangle",
    description=(
        "삼각형 넓이 (base * height) / 2 를 Decimal 로 계산한다. "
        "base 는 밑변, height 는 그 밑변에 수직인 높이이며 둘 다 0 이상 Decimal 문자열, 단위는 같아야 한다. "
        "float 를 거치지 않는다. "
        "비스듬한 변의 길이를 height 로 넣으면 틀리므로 수직 높이를 넣는다."
    ),
    version="1.0.0",
)
def area_triangle(base: str, height: str) -> AreaTriangleResult:
    """Compute the area of a triangle: (base * height) / 2.

    Args:
        base:   Base length as Decimal string (non-negative).
        height: Height as Decimal string (non-negative).

    Returns:
        {area: str, trace}
    """
    trace = CalcTrace(tool="geometry.area_triangle", formula="(base * height) / 2")
    trace.input("base",   base)
    trace.input("height", height)

    b = _parse_decimal(base,   "base")
    h = _parse_decimal(height, "height")

    if b < 0:
        raise DomainConstraintError(f"base 는 음수가 될 수 없습니다: {b}")
    if h < 0:
        raise DomainConstraintError(f"height 는 음수가 될 수 없습니다: {h}")

    area = (b * h) / D("2")

    trace.step("area", str(area))
    trace.output({"area": str(area)})

    return {"area": str(area), "trace": trace.to_dict()}


class AreaRectangleResult(TracedResult):
    area: str


@REGISTRY.tool(
    namespace="geometry",
    name="area_rectangle",
    description=(
        "직사각형 넓이 width * height 를 Decimal 로 계산한다. "
        "두 값은 0 이상 Decimal 문자열이며 단위는 같아야 하고 float 를 거치지 않는다. "
        "대각선 길이나 둘레를 넣으면 의미 없는 값이 나온다. "
        "정사각형은 두 값에 같은 변 길이를 넣는다."
    ),
    version="1.0.0",
)
def area_rectangle(width: str, height: str) -> AreaRectangleResult:
    """Compute the area of a rectangle: width * height.

    Args:
        width:  Width as Decimal string (non-negative).
        height: Height as Decimal string (non-negative).

    Returns:
        {area: str, trace}
    """
    trace = CalcTrace(tool="geometry.area_rectangle", formula="width * height")
    trace.input("width",  width)
    trace.input("height", height)

    w = _parse_decimal(width,  "width")
    h = _parse_decimal(height, "height")

    if w < 0:
        raise DomainConstraintError(f"width 는 음수가 될 수 없습니다: {w}")
    if h < 0:
        raise DomainConstraintError(f"height 는 음수가 될 수 없습니다: {h}")

    area = w * h

    trace.step("area", str(area))
    trace.output({"area": str(area)})

    return {"area": str(area), "trace": trace.to_dict()}


class AreaPolygonResult(TracedResult):
    area: str


@REGISTRY.tool(
    namespace="geometry",
    name="area_polygon",
    description=(
        "다각형 넓이를 신발끈 공식(Shoelace)으로 계산한다. "
        "vertices 는 [[x, y], ...] 형태 Decimal 문자열 좌표이고 꼭짓점 3개 이상을 변을 따라 순서대로 준다. "
        "마지막 점은 첫 점과 자동으로 이어지며 결과는 항상 0 이상이다. "
        "변이 서로 교차하거나 점 순서가 뒤섞이면 실제 면적과 다르다."
    ),
    version="1.0.0",
)
def area_polygon(vertices: list[list[str]]) -> AreaPolygonResult:
    """Compute the area of a polygon using the Shoelace formula.

    Vertices must be provided in order (clockwise or counter-clockwise).
    The polygon is automatically closed (last vertex connects to first).

    Args:
        vertices: List of [x, y] coordinate pairs as Decimal strings.
                  Minimum 3 vertices required.

    Returns:
        {area: str, trace}, area is always non-negative.
    """
    trace = CalcTrace(
        tool="geometry.area_polygon",
        formula="0.5 * |Σ (x_i * y_{i+1} - x_{i+1} * y_i)|",
    )
    trace.input("vertices", vertices)

    if len(vertices) < 3:
        raise DomainConstraintError(
            f"다각형은 최소 3개의 꼭짓점이 필요합니다. 입력: {len(vertices)}개"
        )

    try:
        points = [(D(str(v[0])), D(str(v[1]))) for v in vertices]
    except Exception as exc:
        raise InvalidInputError(f"vertices 형식 오류: {exc}") from exc

    n = len(points)
    total = D("0")
    for i in range(n):
        x_i,     y_i     = points[i]
        x_next,  y_next  = points[(i + 1) % n]
        total += x_i * y_next - x_next * y_i

    area = abs(total) / D("2")

    trace.step("shoelace_sum", str(total))
    trace.step("area",         str(area))
    trace.output({"area": str(area)})

    return {"area": str(area), "trace": trace.to_dict()}
