"""Gear and bearing engineering tools (Tier 3).

Tools:
  - gear_ratio               : i = N_driven / N_driver
  - gear_torque_transmission : τ_out = τ_in · i · η
  - bearing_life_l10         : L10 = (C / P)^p  [×10⁶ rev]
  - bearing_equivalent_load  : P = X·Fr + Y·Fa

ADR-001 Decimal, ADR-003 trace, ADR-007 stateless.
비정수 거듭제곱(10/3 등)은 mpmath workdps(50) → mpmath_to_decimal(digits=30).
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

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_MP_DPS  = 50
_OUT_DIG = 30

_BEARING_TYPES = frozenset({"ball", "roller"})


def _pow_mp(base: Decimal, exponent: Decimal) -> Decimal:
    if base <= _ZERO:
        raise InvalidInputError("거듭제곱의 밑은 0 초과여야 합니다.")
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(
            mpmath.power(mpmath.mpf(str(base)), mpmath.mpf(str(exponent))),
            digits=_OUT_DIG,
        )


# ---------------------------------------------------------------------------
# Gear ratio
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="gear_ratio",
    description=(
        "기어비 i = N_driven / N_driver (치차수 기준). "
        "i > 1 감속, i < 1 증속."
    ),
    version="1.0.0",
)
def gear_ratio(
    teeth_driver:  str,
    teeth_driven:  str,
) -> dict[str, Any]:
    """Compute simple gear ratio."""
    trace = CalcTrace(tool="engineering.gear_ratio", formula="i = N_driven / N_driver")
    nd_d = D(teeth_driver)
    nn_d = D(teeth_driven)
    if nd_d <= _ZERO or nn_d <= _ZERO:
        raise InvalidInputError("teeth_driver, teeth_driven는 0 초과여야 합니다.")

    trace.input("teeth_driver", teeth_driver)
    trace.input("teeth_driven", teeth_driven)

    ratio = div(nn_d, nd_d)
    direction = "reduction" if ratio > _ONE else ("overdrive" if ratio < _ONE else "direct")

    trace.step("ratio",     str(ratio))
    trace.step("direction", direction)
    trace.output({"ratio": str(ratio), "direction": direction})
    return {"ratio": str(ratio), "direction": direction, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Gear torque transmission
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="gear_torque_transmission",
    description=(
        "기어 토크 전달: τ_out = τ_in · i · η. "
        "i=N_driven/N_driver, η 효율 ∈ [0, 1]."
    ),
    version="1.0.0",
)
def gear_torque_transmission(
    input_torque:   str,
    teeth_driver:   str,
    teeth_driven:   str,
    efficiency:     str = "1",
) -> dict[str, Any]:
    """Compute output torque after gear transmission with efficiency loss."""
    trace = CalcTrace(
        tool="engineering.gear_torque_transmission",
        formula="τ_out = τ_in · (N_driven/N_driver) · η",
    )
    t_in = D(input_torque)
    nd_d = D(teeth_driver)
    nn_d = D(teeth_driven)
    eta_d = D(efficiency)
    if nd_d <= _ZERO or nn_d <= _ZERO:
        raise InvalidInputError("teeth_driver, teeth_driven는 0 초과여야 합니다.")
    if eta_d < _ZERO or eta_d > _ONE:
        raise InvalidInputError("efficiency는 [0, 1] 범위여야 합니다.")

    trace.input("input_torque", input_torque)
    trace.input("teeth_driver", teeth_driver)
    trace.input("teeth_driven", teeth_driven)
    trace.input("efficiency",   efficiency)

    ratio = div(nn_d, nd_d)
    t_out = mul(mul(t_in, ratio), eta_d)

    trace.step("ratio",         str(ratio))
    trace.step("output_torque", str(t_out))
    trace.output({"output_torque": str(t_out), "ratio": str(ratio)})
    return {
        "output_torque": str(t_out),
        "ratio":         str(ratio),
        "trace":         trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Bearing basic rating life (L10)
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="bearing_life_l10",
    description=(
        "베어링 기본정격수명 L10 = (C / P)^p [×10⁶ rev]. "
        "bearing_type='ball' → p=3, 'roller' → p=10/3."
    ),
    version="1.0.0",
)
def bearing_life_l10(
    dynamic_capacity: str,
    equivalent_load:  str,
    bearing_type:     str,
) -> dict[str, Any]:
    """Compute basic rating life L10 in millions of revolutions."""
    trace = CalcTrace(
        tool="engineering.bearing_life_l10",
        formula="L10 = (C/P)^p, p(ball)=3, p(roller)=10/3",
    )
    if bearing_type not in _BEARING_TYPES:
        raise InvalidInputError(
            f"bearing_type은 {sorted(_BEARING_TYPES)} 중 하나여야 합니다."
        )
    c_d = D(dynamic_capacity)
    p_d = D(equivalent_load)
    if c_d <= _ZERO:
        raise InvalidInputError("dynamic_capacity는 0 초과여야 합니다.")
    if p_d <= _ZERO:
        raise InvalidInputError("equivalent_load는 0 초과여야 합니다.")

    trace.input("dynamic_capacity", dynamic_capacity)
    trace.input("equivalent_load",  equivalent_load)
    trace.input("bearing_type",     bearing_type)

    ratio = div(c_d, p_d)
    if bearing_type == "ball":
        exponent = Decimal("3")
        # integer exponent — use direct Decimal power for exactness
        life = mul(mul(ratio, ratio), ratio)
    else:
        exponent = div(Decimal("10"), Decimal("3"))
        life = _pow_mp(ratio, exponent)

    trace.step("ratio",    str(ratio))
    trace.step("exponent", str(exponent))
    trace.step("l10_mrev", str(life))
    trace.output(str(life))

    return {
        "l10_million_revolutions": str(life),
        "exponent":                str(exponent),
        "trace":                   trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Bearing equivalent load P = X·Fr + Y·Fa
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="bearing_equivalent_load",
    description=(
        "베어링 등가하중 P = X·Fr + Y·Fa. "
        "X, Y는 베어링 카탈로그의 반경·축 하중 계수. "
        "순수 반경 하중만 있으면 Fa=0, Y=0으로 전달."
    ),
    version="1.0.0",
)
def bearing_equivalent_load(
    radial_load:  str,
    axial_load:   str,
    x_factor:     str,
    y_factor:     str,
) -> dict[str, Any]:
    """Compute dynamic equivalent load P for a rolling-element bearing."""
    trace = CalcTrace(
        tool="engineering.bearing_equivalent_load",
        formula="P = X·Fr + Y·Fa",
    )
    fr = D(radial_load)
    fa = D(axial_load)
    x = D(x_factor)
    y = D(y_factor)
    if fr < _ZERO or fa < _ZERO:
        raise InvalidInputError("radial_load, axial_load는 0 이상이어야 합니다.")
    if x < _ZERO or y < _ZERO:
        raise InvalidInputError("x_factor, y_factor는 0 이상이어야 합니다.")
    if fr == _ZERO and fa == _ZERO:
        raise InvalidInputError("radial_load와 axial_load 모두 0일 수 없습니다.")

    trace.input("radial_load", radial_load)
    trace.input("axial_load",  axial_load)
    trace.input("x_factor",    x_factor)
    trace.input("y_factor",    y_factor)

    load = mul(x, fr) + mul(y, fa)
    trace.step("equivalent_load", str(load))
    trace.output(str(load))

    return {"equivalent_load": str(load), "trace": trace.to_dict()}
