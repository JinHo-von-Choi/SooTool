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
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_TWO     = Decimal("2")
_THREE   = Decimal("3")
_HALF    = Decimal("0.5")


# ---------------------------------------------------------------------------
# Stress σ = F / A
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="mech_stress",
    description="응력 σ = F / A (Pa = N/m²).",
    version="1.0.0",
)
def mech_stress(force: str, area: str) -> dict[str, Any]:
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

    return {"stress": str(stress), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Strain ε = ΔL / L
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="mech_strain",
    description="변형률 ε = ΔL / L (무차원).",
    version="1.0.0",
)
def mech_strain(delta_length: str, original_length: str) -> dict[str, Any]:
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

    return {"strain": str(strain), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Elastic modulus relations: E, G, ν, K
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="elastic_modulus_relate",
    description=(
        "선형 탄성 관계식으로 E(Young), G(전단), nu(푸아송), K(체적) 중 2개 입력 → "
        "나머지 2개 계산. 등방성 재료 가정."
    ),
    version="1.0.0",
)
def elastic_modulus_relate(
    young:     str | None = None,
    shear:     str | None = None,
    poisson:   str | None = None,
    bulk:      str | None = None,
) -> dict[str, Any]:
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

    return {
        "young":   str(e_d),
        "shear":   str(g_d),
        "poisson": str(nu_d),
        "bulk":    str(k_d),
        "trace":   trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Torque × angular velocity → power
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="torque_rotational_power",
    description="회전 일률 P = τ · ω (W = N·m × rad/s).",
    version="1.0.0",
)
def torque_rotational_power(torque: str, angular_velocity: str) -> dict[str, Any]:
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

    return {"power": str(power), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Moment of inertia for standard shapes
# ---------------------------------------------------------------------------


_MOI_SHAPES = frozenset({"solid_disk", "thin_ring", "thin_rod_center", "thin_rod_end", "solid_sphere"})


@REGISTRY.tool(
    namespace="engineering",
    name="moment_of_inertia",
    description=(
        "표준 형상의 관성 모멘트. shapes: "
        "solid_disk (½mr²), thin_ring (mr²), thin_rod_center (1/12 mL²), "
        "thin_rod_end (1/3 mL²), solid_sphere (2/5 mr²)."
    ),
    version="1.0.0",
)
def moment_of_inertia(
    shape:  str,
    mass:   str,
    radius: str | None = None,
    length: str | None = None,
) -> dict[str, Any]:
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

    return {"moment_of_inertia": str(moi), "trace": trace.to_dict()}
