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
from typing import Any, NotRequired

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_MPDPS = 40
_MP_LOCK = threading.Lock()


class SnellLawResult(TracedResult):
    theta2: str
    unit:   str


class ThinLensResult(TracedResult):
    magnification: str
    focal_length:  NotRequired[str]
    object_dist:   NotRequired[str]
    image_dist:    NotRequired[str]


class BraggResult(TracedResult):
    wavelength: NotRequired[str]
    spacing:    NotRequired[str]
    angle:      NotRequired[str]
    unit:       NotRequired[str]


class IntensityResult(TracedResult):
    intensity: str
    unit:      str


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
        "스넬의 법칙으로 굴절각을 계산한다. n1 sin(theta1) = n2 sin(theta2), theta2 = asin(n1/n2 * sin(theta1)). "
        "n1, n2는 양수 굴절률, theta1은 입사각이며 모두 Decimal 문자열이다. unit='deg'(기본) 또는 'rad'이고 결과도 같은 단위다. "
        "mpmath 40자리 계산 후 유효숫자 20자리로 돌려준다. 전반사가 일어나는 입사각이면 오류이며 "
        "각도는 법선 기준이다(표면 기준 각을 넣으면 안 된다)."
    ),
    version="1.0.0",
)
def snell_law(
    n1:       str,
    n2:       str,
    theta1:   str,
    unit:     str = "deg",
) -> SnellLawResult:
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
        "얇은 렌즈 방정식 1/f = 1/p + 1/q에서 빠진 값 하나(초점거리, 물체거리, 상거리)를 구하고 배율 m = -q/p도 돌려준다. "
        "세 인자 중 정확히 2개를 Decimal 문자열로 주며 길이 단위는 통일한다. 반올림하지 않으며 0 거리나 "
        "평행광선(무한대) 조합은 오류다. 실상은 양, 허상은 음의 거리 부호 규약을 따르므로 부호를 맞춰 넣어야 한다."
    ),
    version="1.0.0",
)
def thin_lens(
    focal_length: str | None = None,
    object_dist:  str | None = None,
    image_dist:   str | None = None,
) -> ThinLensResult:
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
        result_name:    result,  # type: ignore[misc]
        "magnification": str(m_mag),
        "trace":         trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="science",
    name="bragg",
    description=(
        "브래그 회절 조건 n*lambda = 2 d sin(theta)에서 파장, 면간격, 회절각 중 하나를 구한다. "
        "order는 양의 정수이고 wavelength, spacing, angle 중 정확히 하나를 생략하며 나머지는 Decimal 문자열이다. "
        "파장과 면간격은 같은 길이 단위로 넣고, angle은 unit='deg'(기본) 또는 'rad'이며 브래그각 theta 기준이다(2theta 아님). "
        "mpmath 40자리 계산 후 유효숫자 20자리로 돌려주며 sin theta가 1을 넘는 조합은 오류다."
    ),
    version="1.0.0",
)
def bragg(
    order:       int,
    wavelength:  str | None = None,
    spacing:     str | None = None,
    angle:       str | None = None,
    unit:        str = "deg",
) -> BraggResult:
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
        "빛이나 복사의 세기(단위 면적당 전력)를 계산한다. I = P / A. power_w는 0 이상 와트, area_m2는 양수 제곱미터의 "
        "Decimal 문자열이며 결과 단위는 W/m^2, 반올림하지 않는다. 입사각에 따른 유효 면적 보정이나 "
        "파장별 분광 세기는 다루지 않는다. 면적을 cm² 단위로 넣으면 안 된다."
    ),
    version="1.0.0",
)
def intensity(
    power_w:  str,
    area_m2:  str,
) -> IntensityResult:
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
