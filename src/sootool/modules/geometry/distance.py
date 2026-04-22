"""Geometry distance tools: Haversine great-circle distance."""
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


@REGISTRY.tool(
    namespace="geometry",
    name="haversine",
    description="하버사인 공식으로 두 지리 좌표 간 대원 거리(km)를 계산합니다. mpmath 사용.",
    version="1.0.0",
)
def haversine(
    lat1: str,
    lon1: str,
    lat2: str,
    lon2: str,
    earth_radius_km: str = "6371",
) -> dict[str, Any]:
    """Compute the great-circle distance between two geographic points.

    Uses the Haversine formula with mpmath for high-precision trigonometry.

    Args:
        lat1:            Latitude of point 1 in degrees (Decimal string).
        lon1:            Longitude of point 1 in degrees (Decimal string).
        lat2:            Latitude of point 2 in degrees (Decimal string).
        lon2:            Longitude of point 2 in degrees (Decimal string).
        earth_radius_km: Earth's radius in km (default "6371").

    Returns:
        {distance_km: str, trace}
    """
    trace = CalcTrace(
        tool="geometry.haversine",
        formula="2R * arcsin(sqrt(sin²(Δlat/2) + cos(lat1)*cos(lat2)*sin²(Δlon/2)))",
    )
    trace.input("lat1",            lat1)
    trace.input("lon1",            lon1)
    trace.input("lat2",            lat2)
    trace.input("lon2",            lon2)
    trace.input("earth_radius_km", earth_radius_km)

    la1 = _parse_decimal(lat1, "lat1")
    lo1 = _parse_decimal(lon1, "lon1")
    la2 = _parse_decimal(lat2, "lat2")
    lo2 = _parse_decimal(lon2, "lon2")
    R   = _parse_decimal(earth_radius_km, "earth_radius_km")

    for val, name in [(la1, "lat1"), (la2, "lat2")]:
        if val < D("-90") or val > D("90"):
            raise DomainConstraintError(
                f"{name} 은(는) -90 ~ 90 범위여야 합니다: {val}"
            )
    for val, name in [(lo1, "lon1"), (lo2, "lon2")]:
        if val < D("-180") or val > D("180"):
            raise DomainConstraintError(
                f"{name} 은(는) -180 ~ 180 범위여야 합니다: {val}"
            )
    if R <= D("0"):
        raise DomainConstraintError(f"earth_radius_km 은 양수여야 합니다: {R}")

    with mpmath.workdps(_MPMATH_DPS):
        # Convert to radians
        to_rad = mpmath.pi / mpmath.mpf("180")
        phi1   = mpmath.mpf(str(la1)) * to_rad
        phi2   = mpmath.mpf(str(la2)) * to_rad
        dphi   = (mpmath.mpf(str(la2)) - mpmath.mpf(str(la1))) * to_rad
        dlam   = (mpmath.mpf(str(lo2)) - mpmath.mpf(str(lo1))) * to_rad

        a = (mpmath.sin(dphi / 2) ** 2
             + mpmath.cos(phi1) * mpmath.cos(phi2) * mpmath.sin(dlam / 2) ** 2)
        c = 2 * mpmath.asin(mpmath.sqrt(a))

        distance = mpmath.mpf(str(R)) * c
        dist_str = mpmath.nstr(distance, 30, strip_zeros=False)

    result = D(dist_str)

    trace.step("a",           str(a))
    trace.step("c_radians",   str(c))
    trace.step("distance_km", str(result))
    trace.output({"distance_km": str(result)})

    return {"distance_km": str(result), "trace": trace.to_dict()}
