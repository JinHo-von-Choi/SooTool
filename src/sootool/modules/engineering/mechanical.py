"""Mechanical engineering tools.

Tools:
  - mech_stress            : σ = F / A
  - mech_strain            : ε = ΔL / L
  - elastic_modulus_relate : Relate E, G, ν, K (bulk) from any 2 inputs
  - torque_rotational_power: P = τ · ω
  - moment_of_inertia      : Standard shapes (disk, thin-ring, thin-rod, solid sphere)

ADR-001 Decimal 의무, ADR-003 감사 로그, ADR-007 stateless.
제곱근이 필요한 경우 mpmath 고정밀 경로 사용(ADR-008).
"""
from __future__ import annotations

from decimal import Decimal
from typing import cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_TWO     = Decimal("2")
_THREE   = Decimal("3")
_HALF    = Decimal("0.5")


# ---------------------------------------------------------------------------
# Stress σ = F / A
# ---------------------------------------------------------------------------


class MechStressResult(TracedResult):
    stress: str


@REGISTRY.tool(
    namespace="engineering",
    name="mech_stress",
    description=(
        "수직응력 σ = F / A 를 계산한다. force 는 힘(N), area 는 단면적(m², 0 초과)이며 결과는 "
        "Pa(N/m²). 단위 변환은 하지 않고 입력 단위 그대로 나누므로 N 과 mm² 를 넣으면 MPa 가 "
        "나온다. force 부호는 유지되며 인장과 압축의 부호 약속은 호출자가 정한다. 반올림 없이 "
        "50자리 유효숫자."
    ),
    version="1.0.0",
)
def mech_stress(force: str, area: str) -> MechStressResult:
    """Compute stress σ = F / A."""
    trace = CalcTrace(tool="engineering.mech_stress", formula="σ = F / A")
    f_d = D(force)
    a_d = D(area)
    if a_d <= _ZERO:
        raise InvalidInputError("area는 0 초과여야 합니다.")

    trace.input("force", force)
    trace.input("area",  area)

    stress = div(f_d, a_d)
    trace.step("stress", str(stress))
    trace.output(str(stress))

    return cast(MechStressResult, {"stress": str(stress), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Strain ε = ΔL / L
# ---------------------------------------------------------------------------


class MechStrainResult(TracedResult):
    strain: str


@REGISTRY.tool(
    namespace="engineering",
    name="mech_strain",
    description=(
        "선형 변형률 ε = ΔL / L (무차원)을 계산한다. delta_length 와 original_length 는 같은 길이 "
        "단위여야 하며(mm 와 m 을 섞으면 틀림) original_length 는 0 초과, delta_length 는 "
        "음수(수축)도 가능하다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def mech_strain(delta_length: str, original_length: str) -> MechStrainResult:
    """Compute linear strain ε = ΔL / L."""
    trace = CalcTrace(tool="engineering.mech_strain", formula="ε = ΔL / L")
    dl_d = D(delta_length)
    l_d  = D(original_length)
    if l_d <= _ZERO:
        raise InvalidInputError("original_length는 0 초과여야 합니다.")

    trace.input("delta_length",    delta_length)
    trace.input("original_length", original_length)

    strain = div(dl_d, l_d)
    trace.step("strain", str(strain))
    trace.output(str(strain))

    return cast(MechStrainResult, {"strain": str(strain), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Elastic modulus relations: E, G, ν, K
# ---------------------------------------------------------------------------


class ElasticModulusRelateResult(TracedResult):
    young:   str
    shear:   str
    poisson: str
    bulk:    str


@REGISTRY.tool(
    namespace="engineering",
    name="elastic_modulus_relate",
    description=(
        "등방성 선형 탄성체에서 영률 E, 전단탄성계수 G, 푸아송비 ν, 체적탄성계수 K 중 정확히 2개를 "
        "받아 나머지 2개를 계산한다(E = 2G(1+ν) = 3K(1−2ν)). 탄성계수는 같은 응력 단위로 0 초과, "
        "푸아송비는 -1 초과 0.5 미만이며 입력이 2개가 아니면 오류. 이방성 재료에는 쓸 수 없다. "
        "반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def elastic_modulus_relate(
    young:     str | None = None,
    shear:     str | None = None,
    poisson:   str | None = None,
    bulk:      str | None = None,
) -> ElasticModulusRelateResult:
    """Relate E, G, ν, K assuming isotropic linear elasticity.

    Standard identities (isotropic):
      E = 2G(1+ν) = 3K(1−2ν)
      G = E / (2(1+ν))
      K = E / (3(1−2ν))
      ν = E/(2G) − 1 = (3K − E)/(6K) = (3K − 2G)/(2(3K + G))

    Provide exactly 2 of {young, shear, poisson, bulk}. The other two are computed.
    """
    trace = CalcTrace(
        tool="engineering.elastic_modulus_relate",
        formula="E = 2G(1+ν) = 3K(1−2ν)",
    )

    given = {
        k: v
        for k, v in [("young", young), ("shear", shear), ("poisson", poisson), ("bulk", bulk)]
        if v is not None
    }
    if len(given) != 2:
        raise InvalidInputError(
            f"정확히 2개의 값을 입력해야 합니다. 현재 {len(given)}개 입력됨: {list(given.keys())}"
        )
    trace.input("given", list(given.keys()))

    e_d = D(young)   if young   is not None else None
    g_d = D(shear)   if shear   is not None else None
    nu_d = D(poisson) if poisson is not None else None
    k_d = D(bulk)    if bulk    is not None else None

    for name, val in [("young", e_d), ("shear", g_d), ("bulk", k_d)]:
        if val is not None and val <= _ZERO:
            raise InvalidInputError(f"{name}는 0 초과여야 합니다.")
    if nu_d is not None and (nu_d <= Decimal("-1") or nu_d >= _HALF):
        raise InvalidInputError("poisson은 (-1, 0.5) 범위여야 합니다.")

    keys = frozenset(given.keys())

    if keys == frozenset({"young", "shear"}):
        assert e_d is not None and g_d is not None
        # ν = E/(2G) − 1 ; K = E / (3(1−2ν))
        nu_d = div(e_d, mul(_TWO, g_d)) - _ONE
        k_d  = div(e_d, mul(_THREE, _ONE - mul(_TWO, nu_d)))

    elif keys == frozenset({"young", "poisson"}):
        assert e_d is not None and nu_d is not None
        g_d = div(e_d, mul(_TWO, _ONE + nu_d))
        k_d = div(e_d, mul(_THREE, _ONE - mul(_TWO, nu_d)))

    elif keys == frozenset({"young", "bulk"}):
        assert e_d is not None and k_d is not None
        nu_d = div(mul(_THREE, k_d) - e_d, mul(Decimal("6"), k_d))
        g_d  = div(e_d, mul(_TWO, _ONE + nu_d))

    elif keys == frozenset({"shear", "poisson"}):
        assert g_d is not None and nu_d is not None
        e_d = mul(_TWO, mul(g_d, _ONE + nu_d))
        k_d = div(e_d, mul(_THREE, _ONE - mul(_TWO, nu_d)))

    elif keys == frozenset({"shear", "bulk"}):
        assert g_d is not None and k_d is not None
        nu_d = div(mul(_THREE, k_d) - mul(_TWO, g_d), mul(_TWO, mul(_THREE, k_d) + g_d))
        e_d  = mul(_TWO, mul(g_d, _ONE + nu_d))

    elif keys == frozenset({"poisson", "bulk"}):
        assert nu_d is not None and k_d is not None
        e_d = mul(_THREE, mul(k_d, _ONE - mul(_TWO, nu_d)))
        g_d = div(e_d, mul(_TWO, _ONE + nu_d))

    else:
        raise InvalidInputError(f"지원하지 않는 입력 조합: {list(given.keys())}")

    trace.step("young",   str(e_d))
    trace.step("shear",   str(g_d))
    trace.step("poisson", str(nu_d))
    trace.step("bulk",    str(k_d))
    trace.output({
        "young":   str(e_d),
        "shear":   str(g_d),
        "poisson": str(nu_d),
        "bulk":    str(k_d),
    })

    return cast(ElasticModulusRelateResult, {
        "young":   str(e_d),
        "shear":   str(g_d),
        "poisson": str(nu_d),
        "bulk":    str(k_d),
        "trace":   trace.to_dict(),
    })


# ---------------------------------------------------------------------------
# Torque × angular velocity → power
# ---------------------------------------------------------------------------


class TorqueRotationalPowerResult(TracedResult):
    power: str


@REGISTRY.tool(
    namespace="engineering",
    name="torque_rotational_power",
    description=(
        "회전 일률 P = τ·ω (W)를 계산한다. torque 는 N·m, angular_velocity 는 rad/s 이다. "
        "rpm 을 그대로 넣으면 틀리므로 ω = 2π·rpm/60 으로 먼저 환산해야 한다. 두 값의 부호는 "
        "그대로 곱해진다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def torque_rotational_power(torque: str, angular_velocity: str) -> TorqueRotationalPowerResult:
    """Compute rotational power P = τ · ω."""
    trace = CalcTrace(
        tool="engineering.torque_rotational_power",
        formula="P = τ × ω",
    )
    tau_d   = D(torque)
    omega_d = D(angular_velocity)

    trace.input("torque",           torque)
    trace.input("angular_velocity", angular_velocity)

    power = mul(tau_d, omega_d)
    trace.step("power", str(power))
    trace.output(str(power))

    return cast(TorqueRotationalPowerResult, {"power": str(power), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Moment of inertia for standard shapes
# ---------------------------------------------------------------------------


_MOI_SHAPES = frozenset({"solid_disk", "thin_ring", "thin_rod_center", "thin_rod_end", "solid_sphere"})


class MomentOfInertiaResult(TracedResult):
    moment_of_inertia: str


@REGISTRY.tool(
    namespace="engineering",
    name="moment_of_inertia",
    description=(
        "표준 형상의 질량 관성모멘트 I (kg·m²)를 계산한다. solid_disk(½mr²), thin_ring(mr²), "
        "solid_sphere(2/5 mr²)는 radius 가, thin_rod_center(mL²/12)와 thin_rod_end(mL²/3)는 "
        "length 가 필요하다. mass 와 치수는 0 초과이며 mass 는 kg, 치수는 m. 막대는 중심 또는 "
        "끝점을 지나는 축 기준이라 다른 축은 평행축 정리를 따로 적용해야 한다. 반올림 없음."
    ),
    version="1.0.0",
)
def moment_of_inertia(
    shape:  str,
    mass:   str,
    radius: str | None = None,
    length: str | None = None,
) -> MomentOfInertiaResult:
    """Compute moment of inertia I for standard shapes.

    Shape requirements:
      - solid_disk / thin_ring / solid_sphere: requires radius
      - thin_rod_center / thin_rod_end:        requires length
    """
    trace = CalcTrace(
        tool="engineering.moment_of_inertia",
        formula="I depends on shape",
    )
    if shape not in _MOI_SHAPES:
        raise InvalidInputError(
            f"shape은 {sorted(_MOI_SHAPES)} 중 하나여야 합니다. 입력: {shape!r}"
        )

    mass_d = D(mass)
    if mass_d <= _ZERO:
        raise InvalidInputError("mass는 0 초과여야 합니다.")

    trace.input("shape", shape)
    trace.input("mass",  mass)

    if shape in ("solid_disk", "thin_ring", "solid_sphere"):
        if radius is None:
            raise InvalidInputError(f"shape={shape}는 radius 파라미터가 필요합니다.")
        r_d = D(radius)
        if r_d <= _ZERO:
            raise InvalidInputError("radius는 0 초과여야 합니다.")
        trace.input("radius", radius)

        if shape == "solid_disk":
            trace.formula = "I = ½ m r²"
            moi = mul(_HALF, mul(mass_d, mul(r_d, r_d)))
        elif shape == "thin_ring":
            trace.formula = "I = m r²"
            moi = mul(mass_d, mul(r_d, r_d))
        else:  # solid_sphere
            trace.formula = "I = (2/5) m r²"
            moi = mul(div(_TWO, Decimal("5")), mul(mass_d, mul(r_d, r_d)))

    else:
        if length is None:
            raise InvalidInputError(f"shape={shape}는 length 파라미터가 필요합니다.")
        l_d = D(length)
        if l_d <= _ZERO:
            raise InvalidInputError("length는 0 초과여야 합니다.")
        trace.input("length", length)

        if shape == "thin_rod_center":
            trace.formula = "I = (1/12) m L²"
            moi = mul(div(_ONE, Decimal("12")), mul(mass_d, mul(l_d, l_d)))
        else:  # thin_rod_end
            trace.formula = "I = (1/3) m L²"
            moi = mul(div(_ONE, _THREE), mul(mass_d, mul(l_d, l_d)))

    trace.step("moment_of_inertia", str(moi))
    trace.output(str(moi))

    return cast(MomentOfInertiaResult, {"moment_of_inertia": str(moi), "trace": trace.to_dict()})
