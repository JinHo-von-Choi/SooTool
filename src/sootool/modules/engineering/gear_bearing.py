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
from typing import Literal, cast

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

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
class GearRatioResult(TracedResult):
    ratio:     str
    direction: Literal["reduction", "overdrive", "direct"]


@REGISTRY.tool(
    namespace="engineering",
    name="gear_ratio",
    description=(
        "단순 기어쌍의 기어비 i = 피동 잇수 / 구동 잇수 를 계산하고 방향을 함께 반환한다. "
        "i > 1 이면 reduction(감속), i < 1 이면 overdrive(증속), 1 이면 direct. 잇수는 0 초과 "
        "숫자 문자열이며 구동과 피동 인수를 바꾸면 역수가 나온다. 다단 기어열은 단별로 구해 곱해야 "
        "한다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def gear_ratio(
    teeth_driver:  str,
    teeth_driven:  str,
) -> GearRatioResult:
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
    return cast(GearRatioResult, {
        "ratio":     str(ratio),
        "direction": direction,
        "trace":     trace.to_dict(),
    })


# ---------------------------------------------------------------------------
# Gear torque transmission
# ---------------------------------------------------------------------------
class GearTorqueTransmissionResult(TracedResult):
    output_torque: str
    ratio:         str


@REGISTRY.tool(
    namespace="engineering",
    name="gear_torque_transmission",
    description=(
        "기어쌍을 통과한 출력 토크 τ_out = τ_in·(피동 잇수/구동 잇수)·η 를 계산하고 기어비도 "
        "반환한다. 출력 토크는 input_torque 와 같은 단위(예: N·m)이고 efficiency 는 기본 1, "
        "[0, 1] 범위의 소수여야 한다(95 가 아니라 0.95). 속도는 기어비에 반비례해 변하므로 출력 "
        "속도는 별도로 구해야 한다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def gear_torque_transmission(
    input_torque:   str,
    teeth_driver:   str,
    teeth_driven:   str,
    efficiency:     str = "1",
) -> GearTorqueTransmissionResult:
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
    return cast(GearTorqueTransmissionResult, {
        "output_torque": str(t_out),
        "ratio":         str(ratio),
        "trace":         trace.to_dict(),
    })


# ---------------------------------------------------------------------------
# Bearing basic rating life (L10)
# ---------------------------------------------------------------------------
class BearingLifeL10Result(TracedResult):
    l10_million_revolutions: str
    exponent:                str


@REGISTRY.tool(
    namespace="engineering",
    name="bearing_life_l10",
    description=(
        "구름 베어링 기본정격수명 L10 = (C/P)^p 를 백만 회전(10⁶ rev) 단위로 계산한다. "
        "bearing_type 'ball' 은 p=3(정확 계산), 'roller' 는 p=10/3(30자리 유효숫자). "
        "dynamic_capacity 와 equivalent_load 는 같은 힘 단위이고 0 초과여야 한다. 신뢰도나 "
        "윤활 보정계수는 적용하지 않으며 등가하중은 bearing_equivalent_load 로 먼저 구한다."
    ),
    version="1.0.0",
)
def bearing_life_l10(
    dynamic_capacity: str,
    equivalent_load:  str,
    bearing_type:     str,
) -> BearingLifeL10Result:
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
        # integer exponent, use direct Decimal power for exactness
        life = mul(mul(ratio, ratio), ratio)
    else:
        exponent = div(Decimal("10"), Decimal("3"))
        life = _pow_mp(ratio, exponent)

    trace.step("ratio",    str(ratio))
    trace.step("exponent", str(exponent))
    trace.step("l10_mrev", str(life))
    trace.output(str(life))

    return cast(BearingLifeL10Result, {
        "l10_million_revolutions": str(life),
        "exponent":                str(exponent),
        "trace":                   trace.to_dict(),
    })


# ---------------------------------------------------------------------------
# Bearing equivalent load P = X·Fr + Y·Fa
# ---------------------------------------------------------------------------
class BearingEquivalentLoadResult(TracedResult):
    equivalent_load: str


@REGISTRY.tool(
    namespace="engineering",
    name="bearing_equivalent_load",
    description=(
        "베어링 동등가하중 P = X·Fr + Y·Fa 를 계산한다. 반경하중, 축하중, 계수 X 와 Y 는 모두 "
        "0 이상이고 두 하중이 동시에 0 이면 오류다. X, Y 는 카탈로그 값을 직접 넣어야 하며 "
        "Fa/Fr 과 e 의 비교로 계수를 고르는 과정은 하지 않는다. 순수 반경하중이면 axial_load 와 "
        "y_factor 를 0 으로 둔다. 결과는 bearing_life_l10 의 equivalent_load 로 쓴다."
    ),
    version="1.0.0",
)
def bearing_equivalent_load(
    radial_load:  str,
    axial_load:   str,
    x_factor:     str,
    y_factor:     str,
) -> BearingEquivalentLoadResult:
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

    return cast(BearingEquivalentLoadResult, {"equivalent_load": str(load), "trace": trace.to_dict()})
