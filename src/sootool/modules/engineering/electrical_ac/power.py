"""Three-phase power and power factor correction tools.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.engineering.electrical_ac._common import (
    _ONE,
    _TWO,
    _ZERO,
    _pi_dec,
    _sqrt_mp,
)


@REGISTRY.tool(
    namespace="engineering",
    name="three_phase_power",
    description=(
        "균형 3상 전력: P = √3 · V_LL · I_L · cos(φ). "
        "connection: 'wye' 또는 'delta' (선간·선전류 수식 동일)."
    ),
    version="1.0.0",
)
def three_phase_power(
    line_voltage: str,
    line_current: str,
    power_factor: str,
    connection:   str = "wye",
) -> dict[str, Any]:
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
        "역률 보정용 병렬 커패시턴스 C = Q_c / (2π f V²), "
        "Q_c = P · (tan φ₁ − tan φ₂)."
    ),
    version="1.0.0",
)
def power_factor_correction(
    real_power:          str,
    current_pf:          str,
    target_pf:           str,
    voltage:             str,
    frequency:           str,
) -> dict[str, Any]:
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
