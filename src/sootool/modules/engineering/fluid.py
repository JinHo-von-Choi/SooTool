"""Fluid mechanics tools.

Tools:
  - fluid_reynolds       : Reynolds number + flow regime (existing)
  - bernoulli            : Bernoulli equation with one missing term solved
  - darcy_weisbach       : Darcy-Weisbach frictional head loss
  - moody_friction_factor: Colebrook implicit friction factor (iterative)
  - hazen_williams       : Hazen-Williams pipe flow rate
  - pump_hydraulic_power : Hydraulic power P = ρ g Q h
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO             = Decimal("0")
_ONE              = Decimal("1")
_TWO              = Decimal("2")
_LAMINAR_LIMIT    = Decimal("2300")
_TURBULENT_LIMIT  = Decimal("4000")
_MP_DPS           = 50
_OUT_DIG          = 30
_COLEBROOK_MAX_ITER  = 100
_COLEBROOK_TOLERANCE = Decimal("1E-10")


def _reynolds_regime(re: Decimal) -> str:
    """Classify flow regime based on Reynolds number."""
    if re < _LAMINAR_LIMIT:
        return "laminar"
    if re > _TURBULENT_LIMIT:
        return "turbulent"
    return "transitional"


@REGISTRY.tool(
    namespace="engineering",
    name="fluid_reynolds",
    description="Reynolds number: Re = ρvL/μ. Classifies flow as laminar/transitional/turbulent.",
    version="1.0.0",
)
def fluid_reynolds(
    density:   str,
    velocity:  str,
    length:    str,
    viscosity: str,
) -> dict[str, Any]:
    """Calculate the Reynolds number and classify the flow regime.

    Formula: Re = (ρ × v × L) / μ

    Flow regime thresholds (pipe flow convention):
      Re < 2300  → laminar
      2300 ≤ Re ≤ 4000 → transitional
      Re > 4000  → turbulent

    Args:
        density:   Fluid density ρ in kg/m³ (Decimal string, > 0).
        velocity:  Flow velocity v in m/s (Decimal string, > 0).
        length:    Characteristic length L in m (Decimal string, > 0).
        viscosity: Dynamic viscosity μ in Pa·s (Decimal string, > 0).

    Returns:
        {reynolds: str, regime: str, trace}

    Raises:
        InvalidInputError: If any parameter is ≤ 0.
    """
    trace = CalcTrace(
        tool="engineering.fluid_reynolds",
        formula="Re = (ρ × v × L) / μ",
    )

    rho_d = D(density)
    v_d   = D(velocity)
    l_d   = D(length)
    mu_d  = D(viscosity)

    for name, val in [("density", rho_d), ("velocity", v_d), ("length", l_d), ("viscosity", mu_d)]:
        if val <= _ZERO:
            raise InvalidInputError(f"{name}는 0 초과여야 합니다.")

    trace.input("density",   density)
    trace.input("velocity",  velocity)
    trace.input("length",    length)
    trace.input("viscosity", viscosity)

    numerator = mul(mul(rho_d, v_d), l_d)
    reynolds  = div(numerator, mu_d)
    regime    = _reynolds_regime(reynolds)

    trace.step("numerator", str(numerator))
    trace.step("reynolds",  str(reynolds))
    trace.step("regime",    regime)
    trace.output({"reynolds": str(reynolds), "regime": regime})

    return {
        "reynolds": str(reynolds),
        "regime":   regime,
        "trace":    trace.to_dict(),
    }


def _sqrt_mp(x: Decimal) -> Decimal:
    """High-precision square root via mpmath."""
    if x < _ZERO:
        raise InvalidInputError("제곱근의 피연산자는 0 이상이어야 합니다.")
    if x == _ZERO:
        return _ZERO
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.sqrt(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _pow_mp(base: Decimal, exponent: Decimal) -> Decimal:
    """Generalised power for positive base via mpmath."""
    if base <= _ZERO:
        raise InvalidInputError("거듭제곱의 밑은 0 초과여야 합니다.")
    with mpmath.workdps(_MP_DPS):
        result = mpmath.power(mpmath.mpf(str(base)), mpmath.mpf(str(exponent)))
        return mpmath_to_decimal(result, digits=_OUT_DIG)


# ---------------------------------------------------------------------------
# Bernoulli equation (solve one missing term)
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="bernoulli",
    description=(
        "베르누이 방정식 P + ½ρv² + ρgz = const. "
        "State 1 완전 입력 + State 2에서 정확히 하나가 None인 항목을 해(解). "
        "비압축성·비점성·정상류 가정."
    ),
    version="1.0.0",
)
def bernoulli(
    pressure_1: str,
    velocity_1: str,
    elevation_1: str,
    density: str,
    pressure_2:  str | None = None,
    velocity_2:  str | None = None,
    elevation_2: str | None = None,
    gravity:     str = "9.80665",
) -> dict[str, Any]:
    """Solve Bernoulli equation for exactly one missing state-2 term.

    P₁ + ½ρv₁² + ρgz₁ = P₂ + ½ρv₂² + ρgz₂

    All state-1 values and density/gravity must be provided.
    Exactly one of (pressure_2, velocity_2, elevation_2) must be None.
    """
    trace = CalcTrace(
        tool="engineering.bernoulli",
        formula="P + ½ρv² + ρgz = const",
    )

    rho_d = D(density)
    g_d   = D(gravity)
    if rho_d <= _ZERO:
        raise InvalidInputError("density는 0 초과여야 합니다.")
    if g_d <= _ZERO:
        raise InvalidInputError("gravity는 0 초과여야 합니다.")

    p1_d = D(pressure_1)
    v1_d = D(velocity_1)
    z1_d = D(elevation_1)
    if v1_d < _ZERO:
        raise InvalidInputError("velocity_1는 0 이상이어야 합니다.")

    unknowns = [p2 is None for p2 in (pressure_2, velocity_2, elevation_2)]
    if sum(unknowns) != 1:
        raise InvalidInputError(
            "pressure_2, velocity_2, elevation_2 중 정확히 1개가 None이어야 합니다."
        )

    trace.input("density",      density)
    trace.input("gravity",      gravity)
    trace.input("pressure_1",   pressure_1)
    trace.input("velocity_1",   velocity_1)
    trace.input("elevation_1",  elevation_1)

    half_rho = div(rho_d, _TWO)
    rho_g    = mul(rho_d, g_d)

    # Total head (same on both sides after multiplying through by 1/ρ or kept as Pa equivalents).
    # Use energy per volume: total = P + ½ρv² + ρgz
    total = p1_d + mul(half_rho, mul(v1_d, v1_d)) + mul(rho_g, z1_d)
    trace.step("total_energy_per_volume", str(total))

    if pressure_2 is None:
        v2_d = D(velocity_2 or "0")
        z2_d = D(elevation_2 or "0")
        if v2_d < _ZERO:
            raise InvalidInputError("velocity_2는 0 이상이어야 합니다.")
        p2 = total - mul(half_rho, mul(v2_d, v2_d)) - mul(rho_g, z2_d)
        trace.step("pressure_2", str(p2))
        trace.output({"pressure_2": str(p2)})
        return {"pressure_2": str(p2), "trace": trace.to_dict()}

    if velocity_2 is None:
        p2_d = D(pressure_2)
        z2_d = D(elevation_2 or "0")
        residual = total - p2_d - mul(rho_g, z2_d)
        v2_sq = div(residual, half_rho)
        if v2_sq < _ZERO:
            raise InvalidInputError(
                "주어진 조건에서 v₂² < 0 (물리적으로 불가능)."
            )
        v2 = _sqrt_mp(v2_sq)
        trace.step("velocity_2", str(v2))
        trace.output({"velocity_2": str(v2)})
        return {"velocity_2": str(v2), "trace": trace.to_dict()}

    # elevation_2 is None
    p2_d = D(pressure_2)
    v2_d = D(velocity_2 or "0")
    if v2_d < _ZERO:
        raise InvalidInputError("velocity_2는 0 이상이어야 합니다.")
    residual = total - p2_d - mul(half_rho, mul(v2_d, v2_d))
    z2 = div(residual, rho_g)
    trace.step("elevation_2", str(z2))
    trace.output({"elevation_2": str(z2)})
    return {"elevation_2": str(z2), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Darcy-Weisbach head loss
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="darcy_weisbach",
    description=(
        "Darcy-Weisbach 마찰 손실 수두 h_f = f · (L/D) · (v²/(2g)). "
        "반환: head_loss_m 및 pressure_drop_pa."
    ),
    version="1.0.0",
)
def darcy_weisbach(
    friction_factor: str,
    length:          str,
    diameter:        str,
    velocity:        str,
    density:         str = "1000",
    gravity:         str = "9.80665",
) -> dict[str, Any]:
    """Compute Darcy-Weisbach head loss (and equivalent pressure drop)."""
    trace = CalcTrace(
        tool="engineering.darcy_weisbach",
        formula="h_f = f × (L/D) × v² / (2g)",
    )
    f_d = D(friction_factor)
    l_d = D(length)
    d_d = D(diameter)
    v_d = D(velocity)
    rho_d = D(density)
    g_d = D(gravity)

    if f_d <= _ZERO:
        raise InvalidInputError("friction_factor는 0 초과여야 합니다.")
    if l_d <= _ZERO or d_d <= _ZERO:
        raise InvalidInputError("length, diameter는 0 초과여야 합니다.")
    if v_d < _ZERO:
        raise InvalidInputError("velocity는 0 이상이어야 합니다.")
    if rho_d <= _ZERO or g_d <= _ZERO:
        raise InvalidInputError("density, gravity는 0 초과여야 합니다.")

    trace.input("friction_factor", friction_factor)
    trace.input("length",          length)
    trace.input("diameter",        diameter)
    trace.input("velocity",        velocity)
    trace.input("density",         density)
    trace.input("gravity",         gravity)

    v_sq      = mul(v_d, v_d)
    two_g     = mul(_TWO, g_d)
    head_loss = mul(f_d, mul(div(l_d, d_d), div(v_sq, two_g)))
    pressure  = mul(rho_d, mul(g_d, head_loss))

    trace.step("head_loss_m", str(head_loss))
    trace.step("pressure_drop_pa", str(pressure))
    trace.output({
        "head_loss_m":       str(head_loss),
        "pressure_drop_pa":  str(pressure),
    })

    return {
        "head_loss_m":      str(head_loss),
        "pressure_drop_pa": str(pressure),
        "trace":            trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Moody friction factor (Colebrook equation, iterative)
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="moody_friction_factor",
    description=(
        "Moody 마찰계수 — Colebrook 방정식 1/√f = -2 log10(ε/(3.7D) + 2.51/(Re √f))을 "
        "최대 100회 반복, 수렴 허용오차 1e-10으로 푼다. "
        "Re<2300 laminar 영역은 64/Re로 즉시 반환."
    ),
    version="1.0.0",
)
def moody_friction_factor(
    reynolds:     str,
    roughness:    str,
    diameter:     str,
) -> dict[str, Any]:
    """Compute the Darcy friction factor via the Colebrook equation.

    Laminar (Re < 2300)     : f = 64 / Re (closed form, not Colebrook).
    Turbulent (Re ≥ 2300)   : Colebrook iterative fixed-point solve.

    Formulation (fixed-point on 1/√f):
        x_{n+1} = -2 log10(ε/(3.7 D) + 2.51 / (Re · x_n))
      with x_n = 1/√f and seed from Swamee-Jain explicit correlation.
    """
    trace = CalcTrace(
        tool="engineering.moody_friction_factor",
        formula="1/√f = -2 log10(ε/(3.7D) + 2.51/(Re √f))",
    )
    re_d = D(reynolds)
    eps_d = D(roughness)
    d_d  = D(diameter)

    if re_d <= _ZERO:
        raise InvalidInputError("reynolds는 0 초과여야 합니다.")
    if eps_d < _ZERO:
        raise InvalidInputError("roughness는 0 이상이어야 합니다.")
    if d_d <= _ZERO:
        raise InvalidInputError("diameter는 0 초과여야 합니다.")

    trace.input("reynolds",  reynolds)
    trace.input("roughness", roughness)
    trace.input("diameter",  diameter)

    if re_d < _LAMINAR_LIMIT:
        friction = div(Decimal("64"), re_d)
        trace.step("regime", "laminar")
        trace.step("friction_factor", str(friction))
        trace.output({"friction_factor": str(friction), "iterations": "0", "regime": "laminar"})
        return {
            "friction_factor": str(friction),
            "iterations":      0,
            "regime":          "laminar",
            "trace":           trace.to_dict(),
        }

    rel_roughness = div(eps_d, d_d)
    term1_const   = div(rel_roughness, Decimal("3.7"))
    term2_const   = div(Decimal("2.51"), re_d)

    # Swamee-Jain explicit seed (valid for turbulent regime):
    #   f_SJ = 0.25 / (log10(ε/(3.7D) + 5.74/Re^0.9))²
    with mpmath.workdps(_MP_DPS):
        inside_mp = (
            mpmath.mpf(str(term1_const))
            + mpmath.mpf("5.74") / mpmath.power(mpmath.mpf(str(re_d)), mpmath.mpf("0.9"))
        )
        if inside_mp <= 0:
            raise InvalidInputError("Swamee-Jain 초기값 인수가 양수가 아닙니다.")
        log_mp = mpmath.log10(inside_mp)
        f_seed_mp = mpmath.mpf("0.25") / (log_mp * log_mp)
        f_seed = mpmath_to_decimal(f_seed_mp, digits=_OUT_DIG)

    x = div(_ONE, _sqrt_mp(f_seed))   # x = 1/√f
    iterations = 0
    converged  = False

    with mpmath.workdps(_MP_DPS):
        t1_mp = mpmath.mpf(str(term1_const))
        t2_mp = mpmath.mpf(str(term2_const))
        x_mp  = mpmath.mpf(str(x))
        tol_mp = mpmath.mpf(str(_COLEBROOK_TOLERANCE))

        for i in range(_COLEBROOK_MAX_ITER):
            iterations = i + 1
            inner = t1_mp + t2_mp * x_mp
            if inner <= 0:
                raise InvalidInputError("Colebrook 반복에서 음수 로그 인수 발생.")
            x_next = -mpmath.mpf("2") * mpmath.log10(inner)
            if abs(x_next - x_mp) < tol_mp:
                x_mp = x_next
                converged = True
                break
            x_mp = x_next

        f_mp = mpmath.mpf("1") / (x_mp * x_mp)
        friction = mpmath_to_decimal(f_mp, digits=_OUT_DIG)

    if not converged:
        raise InvalidInputError(
            f"Colebrook 방정식이 {_COLEBROOK_MAX_ITER}회 내에 수렴하지 않았습니다."
        )

    trace.step("regime", "turbulent")
    trace.step("friction_factor", str(friction))
    trace.step("iterations", str(iterations))
    trace.output({
        "friction_factor": str(friction),
        "iterations":      str(iterations),
        "regime":          "turbulent",
    })

    return {
        "friction_factor": str(friction),
        "iterations":      iterations,
        "regime":          "turbulent",
        "trace":           trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Hazen-Williams pipe flow rate
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="hazen_williams_flow",
    description=(
        "Hazen-Williams 식으로 파이프 유량 Q 계산. "
        "SI 단위: Q = 0.278 · C · D^2.63 · S^0.54 (m³/s), "
        "S = h_f / L."
    ),
    version="1.0.0",
)
def hazen_williams_flow(
    coefficient:  str,
    diameter:     str,
    head_loss:    str,
    length:       str,
) -> dict[str, Any]:
    """Compute flow rate via Hazen-Williams (SI form)."""
    trace = CalcTrace(
        tool="engineering.hazen_williams_flow",
        formula="Q = 0.278 C D^2.63 S^0.54",
    )

    c_d   = D(coefficient)
    d_d   = D(diameter)
    hl_d  = D(head_loss)
    l_d   = D(length)

    if c_d <= _ZERO:
        raise InvalidInputError("coefficient는 0 초과여야 합니다.")
    if d_d <= _ZERO:
        raise InvalidInputError("diameter는 0 초과여야 합니다.")
    if l_d <= _ZERO:
        raise InvalidInputError("length는 0 초과여야 합니다.")
    if hl_d < _ZERO:
        raise InvalidInputError("head_loss는 0 이상이어야 합니다.")

    trace.input("coefficient", coefficient)
    trace.input("diameter",    diameter)
    trace.input("head_loss",   head_loss)
    trace.input("length",      length)

    slope = div(hl_d, l_d)
    d_pow = _pow_mp(d_d, Decimal("2.63"))
    if slope == _ZERO:
        flow = _ZERO
    else:
        s_pow = _pow_mp(slope, Decimal("0.54"))
        flow  = mul(Decimal("0.278"), mul(c_d, mul(d_pow, s_pow)))

    trace.step("hydraulic_slope", str(slope))
    trace.step("flow_rate",       str(flow))
    trace.output(str(flow))

    return {"flow_rate_m3s": str(flow), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Pump hydraulic power
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="pump_hydraulic_power",
    description=(
        "펌프 수력 동력 P_hyd = ρ g Q H. "
        "efficiency가 주어지면 shaft_power = P_hyd / η도 반환."
    ),
    version="1.0.0",
)
def pump_hydraulic_power(
    density:     str,
    flow_rate:   str,
    head:        str,
    gravity:     str = "9.80665",
    efficiency:  str | None = None,
) -> dict[str, Any]:
    """Compute hydraulic (and optionally shaft) power for a pump."""
    trace = CalcTrace(
        tool="engineering.pump_hydraulic_power",
        formula="P_hyd = ρ g Q H",
    )

    rho_d = D(density)
    q_d   = D(flow_rate)
    h_d   = D(head)
    g_d   = D(gravity)

    if rho_d <= _ZERO or g_d <= _ZERO:
        raise InvalidInputError("density, gravity는 0 초과여야 합니다.")
    if q_d < _ZERO:
        raise InvalidInputError("flow_rate는 0 이상이어야 합니다.")
    if h_d < _ZERO:
        raise InvalidInputError("head는 0 이상이어야 합니다.")

    trace.input("density",   density)
    trace.input("flow_rate", flow_rate)
    trace.input("head",      head)
    trace.input("gravity",   gravity)

    hyd_power = mul(rho_d, mul(g_d, mul(q_d, h_d)))
    trace.step("hydraulic_power", str(hyd_power))

    result: dict[str, Any] = {
        "hydraulic_power_w": str(hyd_power),
        "trace":             trace.to_dict(),
    }

    if efficiency is not None:
        eta_d = D(efficiency)
        if eta_d <= _ZERO or eta_d > _ONE:
            raise InvalidInputError("efficiency는 (0, 1] 범위여야 합니다.")
        trace.input("efficiency", efficiency)
        shaft = div(hyd_power, eta_d)
        trace.step("shaft_power", str(shaft))
        result["shaft_power_w"] = str(shaft)
        # update trace dict
        result["trace"] = trace.to_dict()

    trace.output(result)
    return result
