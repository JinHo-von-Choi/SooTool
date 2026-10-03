"""Three-phase power and power factor correction tools.
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.engineering.electrical_ac._common import (
    _ONE,
    _TWO,
    _ZERO,
    _pi_dec,
    _sqrt_mp,
)


class ThreePhasePowerResult(TracedResult):
    """균형 3상 전력. 값은 Decimal 문자열(VA, W, VAR)."""

    apparent: str
    real:     str
    reactive: str


class PowerFactorCorrectionResult(TracedResult):
    """역률 보정 결과. capacitance(F)와 reactive_power_canceled(VAR)는 Decimal 문자열."""

    capacitance:             str
    reactive_power_canceled: str


@REGISTRY.tool(
    namespace="engineering",
    name="three_phase_power",
    description=(
        "균형 3상 회로의 피상, 유효, 무효 전력을 선간 값으로 구한다. S=√3·V_LL·I_L, P=S·cosφ, "
        "Q=√(S²−P²). line_voltage(V)와 line_current(A)는 0 초과, power_factor는 -1 이상 1 이하 "
        "Decimal 문자열. connection('wye'/'delta')은 검증만 하고 수식은 같다. "
        "Q는 항상 0 이상이라 진상 지상을 구분하지 못한다."
    ),
    version="1.0.0",
)
def three_phase_power(
    line_voltage: str,
    line_current: str,
    power_factor: str,
    connection:   str = "wye",
) -> ThreePhasePowerResult:
    """Compute balanced three-phase real, reactive, and apparent power.

    Formulas (line quantities):
      S = √3 · V_LL · I_L        (apparent, VA)
      P = S · cos(φ)             (real, W)
      Q = S · sin(φ) = √(S² − P²) (reactive, VAR)
    """
    trace = CalcTrace(
        tool="engineering.three_phase_power",
        formula="S = √3 V_LL I_L; P = S cosφ; Q = √(S² − P²)",
    )
    if connection not in ("wye", "delta"):
        raise InvalidInputError("connection은 'wye' 또는 'delta'여야 합니다.")

    v_d  = D(line_voltage)
    i_d  = D(line_current)
    pf_d = D(power_factor)
    if v_d <= _ZERO or i_d <= _ZERO:
        raise InvalidInputError("line_voltage, line_current는 0 초과여야 합니다.")
    if pf_d < Decimal("-1") or pf_d > _ONE:
        raise InvalidInputError("power_factor는 [-1, 1] 범위여야 합니다.")

    trace.input("line_voltage", line_voltage)
    trace.input("line_current", line_current)
    trace.input("power_factor", power_factor)
    trace.input("connection",   connection)

    sqrt3 = _sqrt_mp(Decimal("3"))
    apparent = mul(sqrt3, mul(v_d, i_d))
    real     = mul(apparent, pf_d)
    reactive_sq = mul(apparent, apparent) - mul(real, real)
    if reactive_sq < _ZERO:
        reactive_sq = _ZERO
    reactive = _sqrt_mp(reactive_sq)

    trace.step("apparent", str(apparent))
    trace.step("real",     str(real))
    trace.step("reactive", str(reactive))
    trace.output({"apparent": str(apparent), "real": str(real), "reactive": str(reactive)})

    return {
        "apparent": str(apparent),
        "real":     str(real),
        "reactive": str(reactive),
        "trace":    trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="engineering",
    name="power_factor_correction",
    description=(
        "지상(유도성) 부하의 역률을 목표 역률로 올리는 병렬 커패시턴스를 구한다. "
        "Q_c=P·(tanφ₁−tanφ₂), C=Q_c/(2π·f·V²). real_power(W), voltage(V), frequency(Hz)는 0 초과, "
        "current_pf와 target_pf는 (0,1] 범위이며 target_pf가 더 커야 한다. 반환: capacitance(F), "
        "reactive_power_canceled(VAR). 오용 주의: 3상은 상별 전력과 커패시터 양단 전압으로 환산해 넣는다."
    ),
    version="1.0.0",
)
def power_factor_correction(
    real_power:          str,
    current_pf:          str,
    target_pf:           str,
    voltage:             str,
    frequency:           str,
) -> PowerFactorCorrectionResult:
    """Compute the shunt capacitance required to correct the power factor.

    Assumes lagging load (inductive).
    """
    trace = CalcTrace(
        tool="engineering.power_factor_correction",
        formula="C = P(tan φ₁ − tan φ₂) / (2π f V²)",
    )

    p_d   = D(real_power)
    pf1_d = D(current_pf)
    pf2_d = D(target_pf)
    v_d   = D(voltage)
    f_d   = D(frequency)

    if p_d <= _ZERO:
        raise InvalidInputError("real_power는 0 초과여야 합니다.")
    if v_d <= _ZERO or f_d <= _ZERO:
        raise InvalidInputError("voltage, frequency는 0 초과여야 합니다.")
    for name, val in [("current_pf", pf1_d), ("target_pf", pf2_d)]:
        if val <= _ZERO or val > _ONE:
            raise InvalidInputError(f"{name}는 (0, 1] 범위여야 합니다.")
    if pf2_d <= pf1_d:
        raise InvalidInputError("target_pf는 current_pf보다 커야 합니다.")

    trace.input("real_power", real_power)
    trace.input("current_pf", current_pf)
    trace.input("target_pf",  target_pf)
    trace.input("voltage",    voltage)
    trace.input("frequency",  frequency)

    # tan φ from cos φ: tan = sqrt(1 - cos²) / cos
    tan1 = div(_sqrt_mp(_ONE - mul(pf1_d, pf1_d)), pf1_d)
    tan2 = div(_sqrt_mp(_ONE - mul(pf2_d, pf2_d)), pf2_d)
    qc   = mul(p_d, tan1 - tan2)

    two_pi = mul(_TWO, _pi_dec())
    denom  = mul(two_pi, mul(f_d, mul(v_d, v_d)))
    c      = div(qc, denom)

    trace.step("tan_phi_1", str(tan1))
    trace.step("tan_phi_2", str(tan2))
    trace.step("reactive_to_cancel", str(qc))
    trace.step("capacitance", str(c))
    trace.output({"capacitance": str(c), "reactive_power_canceled": str(qc)})

    return {
        "capacitance":              str(c),
        "reactive_power_canceled":  str(qc),
        "trace":                    trace.to_dict(),
    }
