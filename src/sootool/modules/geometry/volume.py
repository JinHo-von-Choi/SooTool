"""Geometry volume tools: sphere, cylinder, cuboid."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_MPMATH_DPS = 50


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name} 은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


def _require_non_negative(value: Decimal, name: str) -> None:
    if value < 0:
        raise DomainConstraintError(f"{name} 은(는) 음수가 될 수 없습니다: {value}")


@REGISTRY.tool(
    namespace="geometry",
    name="volume_sphere",
    description="구의 부피: (4/3) * π * r³. mpmath 고정밀 π 사용.",
    version="1.0.0",
)
def volume_sphere(radius: str) -> dict[str, Any]:
    """Compute the volume of a sphere: (4/3) * π * r³.

    Args:
        radius: Radius as Decimal string (non-negative).

    Returns:
        {volume: str, trace}
    """
    trace = CalcTrace(tool="geometry.volume_sphere", formula="(4/3) * π * r³")
    trace.input("radius", radius)

    r = _parse_decimal(radius, "radius")
    _require_non_negative(r, "radius")

    with mpmath.workdps(_MPMATH_DPS):
        r_mp   = mpmath.mpf(str(r))
        volume = (mpmath.mpf("4") / mpmath.mpf("3")) * mpmath.pi * r_mp ** 3
        vol_str = mpmath.nstr(volume, 30, strip_zeros=False)

    result = D(vol_str)

    trace.step("volume", str(result))
    trace.output({"volume": str(result)})

    return {"volume": str(result), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="geometry",
    name="volume_cylinder",
    description="원기둥 부피: π * r² * h. mpmath 고정밀 π 사용.",
    version="1.0.0",
)
def volume_cylinder(radius: str, height: str) -> dict[str, Any]:
    """Compute the volume of a cylinder: π * r² * h.

    Args:
        radius: Radius as Decimal string (non-negative).
        height: Height as Decimal string (non-negative).

    Returns:
        {volume: str, trace}
    """
    trace = CalcTrace(tool="geometry.volume_cylinder", formula="π * r² * h")
    trace.input("radius", radius)
    trace.input("height", height)

    r = _parse_decimal(radius, "radius")
    h = _parse_decimal(height, "height")

    _require_non_negative(r, "radius")
    _require_non_negative(h, "height")

    with mpmath.workdps(_MPMATH_DPS):
        r_mp   = mpmath.mpf(str(r))
        h_mp   = mpmath.mpf(str(h))
        volume = mpmath.pi * r_mp * r_mp * h_mp
        vol_str = mpmath.nstr(volume, 30, strip_zeros=False)

    result = D(vol_str)

    trace.step("volume", str(result))
    trace.output({"volume": str(result)})

    return {"volume": str(result), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="geometry",
    name="volume_cuboid",
    description="직육면체 부피: length * width * height. 순수 Decimal 연산.",
    version="1.0.0",
)
def volume_cuboid(length: str, width: str, height: str) -> dict[str, Any]:
    """Compute the volume of a cuboid: length * width * height.

    Args:
        length: Length as Decimal string (non-negative).
        width:  Width as Decimal string (non-negative).
        height: Height as Decimal string (non-negative).

    Returns:
        {volume: str, trace}
    """
    trace = CalcTrace(tool="geometry.volume_cuboid", formula="length * width * height")
    trace.input("length", length)
    trace.input("width",  width)
    trace.input("height", height)

    ln = _parse_decimal(length, "length")
    w  = _parse_decimal(width,  "width")
    h  = _parse_decimal(height, "height")

    _require_non_negative(ln, "length")
    _require_non_negative(w, "width")
    _require_non_negative(h, "height")

    volume = ln * w * h

    trace.step("volume", str(volume))
    trace.output({"volume": str(volume)})

    return {"volume": str(volume), "trace": trace.to_dict()}
