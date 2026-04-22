"""Fluid mechanics tools: Reynolds number calculation."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO             = Decimal("0")
_LAMINAR_LIMIT    = Decimal("2300")
_TURBULENT_LIMIT  = Decimal("4000")


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
