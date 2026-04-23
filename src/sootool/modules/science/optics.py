"""Optics: Snell's law, thin lens equation, Bragg diffraction, intensity.

내부 자료형 (ADR-008):
- 각도 연산은 mpmath 경유. 입출력은 도(degree) 옵션 또는 라디안(radian).
- 길이·세기 등 단위는 Decimal 입출력.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_MPDPS = 40
_MP_LOCK = threading.Lock()


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) Decimal 문자열이어야 합니다: {value!r}") from exc


def _to_radians(angle: Decimal, unit: str) -> Any:
    """Convert an angle (Decimal) to mpmath radians."""
    if unit == "deg":
        return mpmath.mpf(str(angle)) * mpmath.pi / 180
    if unit == "rad":
        return mpmath.mpf(str(angle))
    raise InvalidInputError(f"angle unit은 'deg'|'rad' 여야 합니다: {unit!r}")


def _from_radians(r: Any, unit: str) -> Decimal:
    if unit == "deg":
        return mpmath_to_decimal(r * 180 / mpmath.pi, digits=20)
    return mpmath_to_decimal(r, digits=20)


@REGISTRY.tool(
    namespace="science",
    name="snell_law",
    description=(
        "스넬의 법칙: n1 sin θ1 = n2 sin θ2. theta2 = asin(n1/n2 * sin θ1). "
        "전반사 발생 시 DomainConstraintError. unit='deg'|'rad' (기본 deg)."
    ),
    version="1.0.0",
)
def snell_law(
    n1:       str,
    n2:       str,
    theta1:   str,
    unit:     str = "deg",
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="science.snell_law",
        formula="n1 sin θ1 = n2 sin θ2",
    )
    n1_d = _parse_decimal(n1, "n1")
    n2_d = _parse_decimal(n2, "n2")
    t1   = _parse_decimal(theta1, "theta1")
    if n1_d <= D("0") or n2_d <= D("0"):
        raise DomainConstraintError("굴절률은 양수여야 합니다.")

    trace.input("n1", n1)
    trace.input("n2", n2)
    trace.input("theta1", theta1)
    trace.input("unit", unit)

    with _MP_LOCK, mpmath.workdps(_MPDPS):
        t1_rad = _to_radians(t1, unit)
        sin_t2 = mpmath.mpf(str(n1_d)) / mpmath.mpf(str(n2_d)) * mpmath.sin(t1_rad)
        if abs(sin_t2) > 1:
            raise DomainConstraintError(
                f"전반사 발생: sin θ2={float(sin_t2):.6f} (|·| > 1). "
                f"임계각을 초과한 입사각."
            )
        t2_rad = mpmath.asin(sin_t2)
        t2_dec = _from_radians(t2_rad, unit)
        sin_t2_dec = mpmath_to_decimal(sin_t2, digits=20)

    t2_str = str(t2_dec)
    trace.step("sin_theta2", str(sin_t2_dec))
    trace.step("theta2",     t2_str)
    trace.output({"theta2": t2_str, "unit": unit})

    return {"theta2": t2_str, "unit": unit, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="science",
    name="thin_lens",
    description=(
        "얇은 렌즈 방정식: 1/f = 1/p + 1/q. q 또는 f 중 하나를 None 으로 두면 나머지 두 값으로 역산. "
        "모든 길이 단위 동일 (예: m, cm). 배율 m = -q / p."
    ),
    version="1.0.0",
)
def thin_lens(
    focal_length: str | None = None,
    object_dist:  str | None = None,
    image_dist:   str | None = None,
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="science.thin_lens",
        formula="1/f = 1/p + 1/q, m = -q/p",
    )
    given = sum(v is not None for v in (focal_length, object_dist, image_dist))
    if given != 2:
        raise InvalidInputError(
            "focal_length / object_dist / image_dist 중 정확히 2개가 주어져야 합니다."
        )

    trace.input("focal_length", focal_length)
    trace.input("object_dist",  object_dist)
    trace.input("image_dist",   image_dist)

    if focal_length is None:
        p = _parse_decimal(object_dist, "object_dist")  # type: ignore[arg-type]
        q = _parse_decimal(image_dist,  "image_dist")   # type: ignore[arg-type]
        if p == D("0") or q == D("0"):
            raise DomainConstraintError("object_dist 또는 image_dist 가 0 입니다.")
        inv = D("1") / p + D("1") / q
        if inv == D("0"):
            raise DomainConstraintError("1/p + 1/q = 0 — 초점거리 역산 불가.")
        f = D("1") / inv
        m_mag = -q / p
        result_name = "focal_length"
        result = str(f)
    elif image_dist is None:
        assert focal_length is not None and object_dist is not None
        f = _parse_decimal(focal_length, "focal_length")
        p = _parse_decimal(object_dist,  "object_dist")
        if f == D("0") or p == D("0"):
            raise DomainConstraintError("focal_length 또는 object_dist 가 0 입니다.")
        inv = D("1") / f - D("1") / p
        if inv == D("0"):
            raise DomainConstraintError("평행광선: image_dist 무한대.")
        q = D("1") / inv
        m_mag = -q / p
        result_name = "image_dist"
        result = str(q)
    else:
        f = _parse_decimal(focal_length, "focal_length")
        q = _parse_decimal(image_dist,   "image_dist")
        if f == D("0") or q == D("0"):
            raise DomainConstraintError("focal_length 또는 image_dist 가 0 입니다.")
        inv = D("1") / f - D("1") / q
        if inv == D("0"):
            raise DomainConstraintError("object_dist 무한대.")
        p = D("1") / inv
        m_mag = -q / p
        result_name = "object_dist"
        result = str(p)

    trace.step(result_name,   result)
    trace.step("magnification", str(m_mag))
    trace.output({result_name: result, "magnification": str(m_mag)})

    return {
        result_name:    result,
        "magnification": str(m_mag),
        "trace":         trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="science",
    name="bragg",
    description=(
        "브래그 회절: nλ = 2d sinθ. 미지값 하나(wavelength|spacing|angle)을 None 으로 지정. "
        "unit='deg'|'rad' (기본 deg)."
    ),
    version="1.0.0",
)
def bragg(
    order:       int,
    wavelength:  str | None = None,
    spacing:     str | None = None,
    angle:       str | None = None,
    unit:        str = "deg",
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="science.bragg",
        formula="n λ = 2 d sinθ",
    )
    if not isinstance(order, int) or isinstance(order, bool) or order <= 0:
        raise InvalidInputError(f"order(n)는 양의 정수여야 합니다: {order!r}")
    unknowns = sum(v is None for v in (wavelength, spacing, angle))
    if unknowns != 1:
        raise InvalidInputError(
            "wavelength, spacing, angle 중 정확히 하나를 None 으로 지정해야 합니다."
        )

    trace.input("order",       order)
    trace.input("wavelength",  wavelength)
    trace.input("spacing",     spacing)
    trace.input("angle",       angle)
    trace.input("unit",        unit)

    with _MP_LOCK, mpmath.workdps(_MPDPS):
        if wavelength is None:
            d_val = _parse_decimal(spacing, "spacing")   # type: ignore[arg-type]
            a_val = _parse_decimal(angle,   "angle")     # type: ignore[arg-type]
            if d_val <= D("0"):
                raise DomainConstraintError("spacing 은 양수여야 합니다.")
            a_rad  = _to_radians(a_val, unit)
            lam_mpf = 2 * mpmath.mpf(str(d_val)) * mpmath.sin(a_rad) / order
            lam_dec = mpmath_to_decimal(lam_mpf, digits=20)
            trace.step("wavelength", str(lam_dec))
            trace.output({"wavelength": str(lam_dec)})
            return {"wavelength": str(lam_dec), "trace": trace.to_dict()}
        if spacing is None:
            l_val = _parse_decimal(wavelength, "wavelength")
            a_val = _parse_decimal(angle,      "angle")   # type: ignore[arg-type]
            if l_val <= D("0"):
                raise DomainConstraintError("wavelength 는 양수여야 합니다.")
            a_rad  = _to_radians(a_val, unit)
            sin_a  = mpmath.sin(a_rad)
            if sin_a == 0:
                raise DomainConstraintError("sin(angle) = 0 — spacing 역산 불가.")
            d_mpf = order * mpmath.mpf(str(l_val)) / (2 * sin_a)
            d_dec = mpmath_to_decimal(d_mpf, digits=20)
            trace.step("spacing", str(d_dec))
            trace.output({"spacing": str(d_dec)})
            return {"spacing": str(d_dec), "trace": trace.to_dict()}
        # angle is None
        l_val = _parse_decimal(wavelength, "wavelength")
        d_val = _parse_decimal(spacing,    "spacing")
        if l_val <= D("0") or d_val <= D("0"):
            raise DomainConstraintError("wavelength, spacing 은 양수여야 합니다.")
        sin_t = order * mpmath.mpf(str(l_val)) / (2 * mpmath.mpf(str(d_val)))
        if abs(sin_t) > 1:
            raise DomainConstraintError(
                f"sin θ > 1 — 해당 차수에서 회절 조건 불성립 (sin θ={float(sin_t):.4f})."
            )
        t_rad = mpmath.asin(sin_t)
        t_dec = _from_radians(t_rad, unit)
        trace.step("angle", str(t_dec))
        trace.output({"angle": str(t_dec), "unit": unit})
        return {"angle": str(t_dec), "unit": unit, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="science",
    name="intensity",
    description=(
        "빛의 강도: I = P / A. P 전력(W), A 면적(m²). 결과 W/m²."
    ),
    version="1.0.0",
)
def intensity(
    power_w:  str,
    area_m2:  str,
) -> dict[str, Any]:
    trace = CalcTrace(tool="science.intensity", formula="I = P / A")
    p = _parse_decimal(power_w, "power_w")
    a = _parse_decimal(area_m2, "area_m2")
    if a <= D("0"):
        raise DomainConstraintError(f"area_m2는 양수여야 합니다: {area_m2}")
    if p < D("0"):
        raise DomainConstraintError(f"power_w는 음수가 될 수 없습니다: {power_w}")

    trace.input("power_w", power_w)
    trace.input("area_m2", area_m2)

    i = p / a
    i_str = str(i)
    trace.step("intensity", i_str)
    trace.output({"intensity": i_str})

    return {"intensity": i_str, "unit": "W/m^2", "trace": trace.to_dict()}
