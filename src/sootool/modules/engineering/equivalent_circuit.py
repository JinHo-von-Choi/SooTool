"""Equivalent circuit tools (Tier 3).

Tools:
  - thevenin_equivalent       : V_th, R_th 계산 (open-circuit V, short-circuit I 기반)
  - norton_equivalent         : I_N = V_th / R_th, R_N = R_th
  - max_power_transfer        : R_L = R_th, P_max = V_th² / (4 R_th)

ADR-001 Decimal, ADR-003 trace, ADR-007 stateless.
순수 사칙연산으로 Decimal 직접 처리.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO = Decimal("0")
_FOUR = Decimal("4")


# ---------------------------------------------------------------------------
# Thevenin equivalent
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="thevenin_equivalent",
    description=(
        "테브난 등가: open-circuit 전압(V_oc)과 short-circuit 전류(I_sc)로부터 "
        "V_th = V_oc, R_th = V_oc / I_sc 산출."
    ),
    version="1.0.0",
)
def thevenin_equivalent(
    open_circuit_voltage:  str,
    short_circuit_current: str,
) -> dict[str, Any]:
    """Compute Thevenin equivalent source voltage and resistance."""
    trace = CalcTrace(
        tool="engineering.thevenin_equivalent",
        formula="V_th = V_oc; R_th = V_oc / I_sc",
    )
    voc = D(open_circuit_voltage)
    isc = D(short_circuit_current)
    if isc <= _ZERO:
        raise InvalidInputError("short_circuit_current는 0 초과여야 합니다.")

    trace.input("open_circuit_voltage",  open_circuit_voltage)
    trace.input("short_circuit_current", short_circuit_current)

    v_th = voc
    r_th = div(voc, isc)

    trace.step("v_th", str(v_th))
    trace.step("r_th", str(r_th))
    trace.output({"v_th": str(v_th), "r_th": str(r_th)})

    return {"v_th": str(v_th), "r_th": str(r_th), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Norton equivalent
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="norton_equivalent",
    description=(
        "노턴 등가: I_N = V_th / R_th, R_N = R_th. "
        "테브난 파라미터로부터 직접 변환."
    ),
    version="1.0.0",
)
def norton_equivalent(
    v_th: str,
    r_th: str,
) -> dict[str, Any]:
    """Convert a Thevenin source (V_th, R_th) to Norton form (I_N, R_N)."""
    trace = CalcTrace(
        tool="engineering.norton_equivalent",
        formula="I_N = V_th / R_th; R_N = R_th",
    )
    v_d = D(v_th)
    r_d = D(r_th)
    if r_d <= _ZERO:
        raise InvalidInputError("r_th는 0 초과여야 합니다.")

    trace.input("v_th", v_th)
    trace.input("r_th", r_th)

    i_n = div(v_d, r_d)
    r_n = r_d

    trace.step("i_n", str(i_n))
    trace.step("r_n", str(r_n))
    trace.output({"i_n": str(i_n), "r_n": str(r_n)})

    return {"i_n": str(i_n), "r_n": str(r_n), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Maximum power transfer
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="max_power_transfer",
    description=(
        "최대 전력 전달 정리: 부하 R_L = R_th일 때 P_max = V_th² / (4 R_th). "
        "반환: optimal_load (= R_th), max_power."
    ),
    version="1.0.0",
)
def max_power_transfer(
    v_th: str,
    r_th: str,
) -> dict[str, Any]:
    """Return optimal load resistance and maximum transferable power."""
    trace = CalcTrace(
        tool="engineering.max_power_transfer",
        formula="R_L = R_th; P_max = V_th² / (4 R_th)",
    )
    v_d = D(v_th)
    r_d = D(r_th)
    if r_d <= _ZERO:
        raise InvalidInputError("r_th는 0 초과여야 합니다.")

    trace.input("v_th", v_th)
    trace.input("r_th", r_th)

    v_sq = mul(v_d, v_d)
    p_max = div(v_sq, mul(_FOUR, r_d))

    trace.step("v_squared", str(v_sq))
    trace.step("p_max",     str(p_max))
    trace.output({"optimal_load": str(r_d), "max_power": str(p_max)})

    return {
        "optimal_load": str(r_d),
        "max_power":    str(p_max),
        "trace":        trace.to_dict(),
    }
