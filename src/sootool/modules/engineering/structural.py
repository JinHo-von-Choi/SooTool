"""Structural engineering tools (Tier 2).

Tools:
  - beam_deflection         : 빔 최대 처짐 (cantilever / simply-supported × 집중·등분포)
  - bending_stress          : 휨응력 σ = M c / I
  - shear_stress            : 전단응력 τ = V Q / (I b) (직사각형은 1.5 V/A)
  - euler_buckling          : 오일러 좌굴 한계하중 P_cr = π² E I / (K L)²
  - section_moment_inertia  : 단면 이차모멘트, 직사각형·원형·I형

ADR-001 Decimal 의무, ADR-003 감사 로그, ADR-007 stateless.
π·√ 등 초월·비정수 멱은 mpmath workdps(50) → mpmath_to_decimal(digits=30).
"""
from __future__ import annotations

from decimal import Decimal
from typing import cast

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_TWO     = Decimal("2")
_THREE   = Decimal("3")
_FOUR    = Decimal("4")
_MP_DPS  = 50
_OUT_DIG = 30


def _pi_dec() -> Decimal:
    """High-precision π as Decimal."""
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.pi, digits=_OUT_DIG)


_BEAM_CASES = frozenset({
    "cantilever_point_end",
    "cantilever_uniform",
    "simply_supported_point_center",
    "simply_supported_uniform",
})

_SECTION_SHAPES = frozenset({"rectangle", "circle", "i_beam"})


# ---------------------------------------------------------------------------
# Beam deflection
# ---------------------------------------------------------------------------
class BeamDeflectionResult(TracedResult):
    deflection: str


@REGISTRY.tool(
    namespace="engineering",
    name="beam_deflection",
    description=(
        "표준 하중 조건의 보 최대 처짐 δ_max 를 계산한다. case: cantilever_point_end(PL³/3EI), "
        "cantilever_uniform(wL⁴/8EI), simply_supported_point_center(PL³/48EI), "
        "simply_supported_uniform(5wL⁴/384EI). length m, young Pa, inertia m⁴, load 는 점하중 N 또는 "
        "등분포하중 N/m(모두 0 초과)이며 처짐은 m. 하중 종류와 case 가 어긋나면 값이 틀리고 전단 "
        "변형은 무시한다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def beam_deflection(
    case:    str,
    length:  str,
    young:   str,
    inertia: str,
    load:    str,
) -> BeamDeflectionResult:
    """Compute maximum beam deflection for canonical load cases.

    Args:
        case:    one of _BEAM_CASES
        length:  span L in meters (> 0)
        young:   Young's modulus E in Pa (> 0)
        inertia: second moment of area I in m⁴ (> 0)
        load:    concentrated load P (N) for point cases or distributed load w (N/m)
                 for uniform cases. Must be > 0.
    """
    trace = CalcTrace(tool="engineering.beam_deflection", formula="")
    if case not in _BEAM_CASES:
        raise InvalidInputError(
            f"case는 {sorted(_BEAM_CASES)} 중 하나여야 합니다. 입력: {case!r}"
        )
    l_d = D(length)
    e_d = D(young)
    i_d = D(inertia)
    q_d = D(load)
    if l_d <= _ZERO:
        raise InvalidInputError("length는 0 초과여야 합니다.")
    if e_d <= _ZERO:
        raise InvalidInputError("young은 0 초과여야 합니다.")
    if i_d <= _ZERO:
        raise InvalidInputError("inertia는 0 초과여야 합니다.")
    if q_d <= _ZERO:
        raise InvalidInputError("load는 0 초과여야 합니다.")

    trace.input("case",    case)
    trace.input("length",  length)
    trace.input("young",   young)
    trace.input("inertia", inertia)
    trace.input("load",    load)

    l2 = mul(l_d, l_d)
    l3 = mul(l2, l_d)
    l4 = mul(l3, l_d)
    ei = mul(e_d, i_d)

    if case == "cantilever_point_end":
        trace.formula = "δ = P L³ / (3 E I)"
        delta = div(mul(q_d, l3), mul(_THREE, ei))
    elif case == "cantilever_uniform":
        trace.formula = "δ = w L⁴ / (8 E I)"
        delta = div(mul(q_d, l4), mul(Decimal("8"), ei))
    elif case == "simply_supported_point_center":
        trace.formula = "δ = P L³ / (48 E I)"
        delta = div(mul(q_d, l3), mul(Decimal("48"), ei))
    else:  # simply_supported_uniform
        trace.formula = "δ = 5 w L⁴ / (384 E I)"
        delta = div(mul(Decimal("5"), mul(q_d, l4)), mul(Decimal("384"), ei))

    trace.step("deflection", str(delta))
    trace.output(str(delta))
    return cast(BeamDeflectionResult, {"deflection": str(delta), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Bending stress
# ---------------------------------------------------------------------------
class BendingStressResult(TracedResult):
    stress: str


@REGISTRY.tool(
    namespace="engineering",
    name="bending_stress",
    description=(
        "휨응력 σ = M·c/I 를 계산한다. moment 는 굽힘모멘트(N·m, 부호 유지), distance_neutral 은 "
        "중립축에서 응력을 구할 섬유까지 거리 c(m, 0 초과), inertia 는 단면 이차모멘트 I(m⁴, 0 초과)이며 "
        "결과는 Pa. 최외곽 응력이 필요하면 c 에 전체 높이가 아니라 중립축에서 바깥 면까지의 거리를 "
        "넣어야 한다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def bending_stress(
    moment:            str,
    distance_neutral:  str,
    inertia:           str,
) -> BendingStressResult:
    """Compute flexural stress σ at a fibre at distance c from the neutral axis."""
    trace = CalcTrace(tool="engineering.bending_stress", formula="σ = M c / I")
    m_d = D(moment)
    c_d = D(distance_neutral)
    i_d = D(inertia)
    if c_d <= _ZERO:
        raise InvalidInputError("distance_neutral은 0 초과여야 합니다.")
    if i_d <= _ZERO:
        raise InvalidInputError("inertia는 0 초과여야 합니다.")

    trace.input("moment",           moment)
    trace.input("distance_neutral", distance_neutral)
    trace.input("inertia",          inertia)

    sigma = div(mul(m_d, c_d), i_d)
    trace.step("sigma", str(sigma))
    trace.output(str(sigma))
    return cast(BendingStressResult, {"stress": str(sigma), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Shear stress
# ---------------------------------------------------------------------------
class ShearStressResult(TracedResult):
    shear_stress: str


@REGISTRY.tool(
    namespace="engineering",
    name="shear_stress",
    description=(
        "횡전단응력 τ 를 모드별로 계산한다. average 는 V/A, rectangular_max 는 1.5V/A(직사각형 단면 "
        "중립축의 최대값, area 필요), general 은 V·Q/(I·b)(first_moment_q, inertia, width 필요). "
        "shear_force 는 N, area 는 m²(0 초과)이고 결과는 Pa. 원형이나 I형 단면에 "
        "rectangular_max 를 쓰면 틀리며 필수 인자가 빠지면 오류. 반올림 없음."
    ),
    version="1.0.0",
)
def shear_stress(
    mode:             str,
    shear_force:      str,
    area:             str | None = None,
    first_moment_q:   str | None = None,
    inertia:          str | None = None,
    width:            str | None = None,
) -> ShearStressResult:
    """Compute transverse shear stress under three formulations."""
    trace = CalcTrace(tool="engineering.shear_stress", formula="")
    if mode not in ("average", "rectangular_max", "general"):
        raise InvalidInputError(
            "mode는 'average', 'rectangular_max', 'general' 중 하나여야 합니다."
        )
    v_d = D(shear_force)

    trace.input("mode",        mode)
    trace.input("shear_force", shear_force)

    if mode in ("average", "rectangular_max"):
        if area is None:
            raise InvalidInputError(f"mode={mode}는 area 파라미터가 필요합니다.")
        a_d = D(area)
        if a_d <= _ZERO:
            raise InvalidInputError("area는 0 초과여야 합니다.")
        trace.input("area", area)
        if mode == "average":
            trace.formula = "τ = V / A"
            tau = div(v_d, a_d)
        else:
            trace.formula = "τ_max = 1.5 V / A"
            tau = div(mul(Decimal("1.5"), v_d), a_d)
    else:
        if first_moment_q is None or inertia is None or width is None:
            raise InvalidInputError(
                "mode='general'은 first_moment_q, inertia, width 모두 필요합니다."
            )
        q_d = D(first_moment_q)
        i_d = D(inertia)
        b_d = D(width)
        if i_d <= _ZERO:
            raise InvalidInputError("inertia는 0 초과여야 합니다.")
        if b_d <= _ZERO:
            raise InvalidInputError("width는 0 초과여야 합니다.")
        trace.input("first_moment_q", first_moment_q)
        trace.input("inertia",        inertia)
        trace.input("width",          width)
        trace.formula = "τ = V Q / (I b)"
        tau = div(mul(v_d, q_d), mul(i_d, b_d))

    trace.step("tau", str(tau))
    trace.output(str(tau))
    return cast(ShearStressResult, {"shear_stress": str(tau), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Euler buckling
# ---------------------------------------------------------------------------
class EulerBucklingResult(TracedResult):
    critical_load: str


@REGISTRY.tool(
    namespace="engineering",
    name="euler_buckling",
    description=(
        "오일러 좌굴 임계하중 P_cr = π²EI/(KL)² (N)를 계산한다. end_condition 으로 K 를 자동 설정"
        "(fixed_free 2, pinned_pinned 1, fixed_pinned 0.699, fixed_fixed 0.5)하거나 "
        "effective_length_factor 를 직접 주되 둘 중 정확히 하나만 지정한다. young Pa, inertia m⁴, "
        "length m. 세장한 기둥의 탄성 좌굴 식이라 짧은 기둥에는 항복 하중보다 크게 나올 수 있다. "
        "π 는 30자리."
    ),
    version="1.0.0",
)
def euler_buckling(
    young:                    str,
    inertia:                  str,
    length:                   str,
    end_condition:            str | None = None,
    effective_length_factor:  str | None = None,
) -> EulerBucklingResult:
    """Compute Euler critical buckling load."""
    trace = CalcTrace(tool="engineering.euler_buckling", formula="P_cr = π² E I / (K L)²")
    e_d = D(young)
    i_d = D(inertia)
    l_d = D(length)
    if e_d <= _ZERO:
        raise InvalidInputError("young은 0 초과여야 합니다.")
    if i_d <= _ZERO:
        raise InvalidInputError("inertia는 0 초과여야 합니다.")
    if l_d <= _ZERO:
        raise InvalidInputError("length는 0 초과여야 합니다.")

    if (end_condition is None) == (effective_length_factor is None):
        raise InvalidInputError(
            "end_condition과 effective_length_factor 중 정확히 하나만 지정해야 합니다."
        )

    if effective_length_factor is not None:
        k_d = D(effective_length_factor)
        if k_d <= _ZERO:
            raise InvalidInputError("effective_length_factor는 0 초과여야 합니다.")
    else:
        mapping = {
            "fixed_free":    Decimal("2"),
            "pinned_pinned": Decimal("1"),
            "fixed_pinned":  Decimal("0.699"),
            "fixed_fixed":   Decimal("0.5"),
        }
        if end_condition not in mapping:
            raise InvalidInputError(
                f"end_condition은 {sorted(mapping)} 중 하나여야 합니다."
            )
        k_d = mapping[end_condition]

    trace.input("young",   young)
    trace.input("inertia", inertia)
    trace.input("length",  length)
    if end_condition is not None:
        trace.input("end_condition", end_condition)
    trace.input("K", str(k_d))

    pi_d  = _pi_dec()
    pi_sq = mul(pi_d, pi_d)
    kl    = mul(k_d, l_d)
    kl_sq = mul(kl, kl)
    p_cr  = div(mul(pi_sq, mul(e_d, i_d)), kl_sq)

    trace.step("pi_sq", str(pi_sq))
    trace.step("P_cr",  str(p_cr))
    trace.output(str(p_cr))
    return cast(EulerBucklingResult, {"critical_load": str(p_cr), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Section second moment of area
# ---------------------------------------------------------------------------
class SectionMomentInertiaResult(TracedResult):
    inertia: str


@REGISTRY.tool(
    namespace="engineering",
    name="section_moment_inertia",
    description=(
        "도심 중립축에 대한 단면 이차모멘트 I 를 계산한다. rectangle(width, height: bh³/12), "
        "circle(diameter: πd⁴/64), i_beam(flange_width, flange_thickness, web_height, "
        "web_thickness: BH³/12 − (B−t_w)·web_height³/12, H = web_height + 2·flange_thickness). "
        "치수는 모두 0 초과이고 m 로 넣으면 m⁴. rectangle 의 height 는 굽힘 방향 치수이며 중공 단면은 "
        "지원하지 않는다. π 는 30자리."
    ),
    version="1.0.0",
)
def section_moment_inertia(
    shape:             str,
    width:             str | None = None,
    height:            str | None = None,
    diameter:          str | None = None,
    flange_width:      str | None = None,
    flange_thickness:  str | None = None,
    web_height:        str | None = None,
    web_thickness:     str | None = None,
) -> SectionMomentInertiaResult:
    """Compute second moment of area I about the neutral (centroidal) axis."""
    trace = CalcTrace(tool="engineering.section_moment_inertia", formula="")
    if shape not in _SECTION_SHAPES:
        raise InvalidInputError(
            f"shape은 {sorted(_SECTION_SHAPES)} 중 하나여야 합니다. 입력: {shape!r}"
        )
    trace.input("shape", shape)

    if shape == "rectangle":
        if width is None or height is None:
            raise InvalidInputError("rectangle은 width, height가 필요합니다.")
        b_d = D(width)
        h_d = D(height)
        if b_d <= _ZERO or h_d <= _ZERO:
            raise InvalidInputError("width, height는 0 초과여야 합니다.")
        trace.input("width",  width)
        trace.input("height", height)
        trace.formula = "I = b h³ / 12"
        h3 = mul(mul(h_d, h_d), h_d)
        inertia = div(mul(b_d, h3), Decimal("12"))

    elif shape == "circle":
        if diameter is None:
            raise InvalidInputError("circle은 diameter가 필요합니다.")
        d_d = D(diameter)
        if d_d <= _ZERO:
            raise InvalidInputError("diameter는 0 초과여야 합니다.")
        trace.input("diameter", diameter)
        trace.formula = "I = π d⁴ / 64"
        d2 = mul(d_d, d_d)
        d4 = mul(d2, d2)
        inertia = div(mul(_pi_dec(), d4), Decimal("64"))

    else:  # i_beam
        if (
            flange_width     is None or
            flange_thickness is None or
            web_height       is None or
            web_thickness    is None
        ):
            raise InvalidInputError(
                "i_beam은 flange_width, flange_thickness, web_height, web_thickness가 모두 필요합니다."
            )
        bf = D(flange_width)
        tf = D(flange_thickness)
        hw = D(web_height)
        tw = D(web_thickness)
        if bf <= _ZERO or tf <= _ZERO or hw <= _ZERO or tw <= _ZERO:
            raise InvalidInputError("I형 단면 입력은 모두 0 초과여야 합니다.")
        if tw > bf:
            raise InvalidInputError("web_thickness는 flange_width 이하여야 합니다.")
        trace.input("flange_width",     flange_width)
        trace.input("flange_thickness", flange_thickness)
        trace.input("web_height",       web_height)
        trace.input("web_thickness",    web_thickness)
        trace.formula = "I = B H³/12 − (B−t_w)(H − 2 t_f)³/12"
        total_h = hw + _TWO * tf
        h3 = mul(mul(total_h, total_h), total_h)
        outer = div(mul(bf, h3), Decimal("12"))
        inner_h = hw  # H − 2 t_f
        inner_h3 = mul(mul(inner_h, inner_h), inner_h)
        inner = div(mul(bf - tw, inner_h3), Decimal("12"))
        inertia = outer - inner

    trace.step("inertia", str(inertia))
    trace.output(str(inertia))
    return cast(SectionMomentInertiaResult, {"inertia": str(inertia), "trace": trace.to_dict()})
