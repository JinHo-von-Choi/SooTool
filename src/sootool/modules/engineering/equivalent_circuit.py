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

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_ZERO = Decimal("0")
_FOUR = Decimal("4")


# ---------------------------------------------------------------------------
# Thevenin equivalent
# ---------------------------------------------------------------------------
class TheveninEquivalentResult(TracedResult):
    """테브난 등가 전압원과 저항. 값은 Decimal 문자열."""

    v_th: str
    r_th: str


class NortonEquivalentResult(TracedResult):
    """노턴 등가 전류원과 병렬 저항. 값은 Decimal 문자열."""

    i_n: str
    r_n: str


class MaxPowerTransferResult(TracedResult):
    """최대 전력 전달 조건. 값은 Decimal 문자열."""

    optimal_load: str
    max_power:    str


@REGISTRY.tool(
    namespace="engineering",
    name="thevenin_equivalent",
    description=(
        "개방 전압과 단락 전류로 테브난 등가 회로를 구한다. V_th=V_oc, R_th=V_oc/I_sc. "
        "open_circuit_voltage(V)와 short_circuit_current(A, 0 초과)는 Decimal 문자열. "
        "반환: v_th, r_th. 오용 주의: 독립 전원이 없는 회로는 V_oc가 0이라 R_th가 0으로 계산되므로 "
        "저항 합성으로 R_th를 구해야 한다."
    ),
    version="1.0.0",
)
def thevenin_equivalent(
    open_circuit_voltage:  str,
    short_circuit_current: str,
) -> TheveninEquivalentResult:
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
        "테브난 등가(V_th, R_th)를 노턴 등가로 변환한다. I_N=V_th/R_th, R_N=R_th. "
        "v_th(V)와 r_th(Ω, 0 초과)는 Decimal 문자열. 반환: i_n(A), r_n(Ω). "
        "오용 주의: 개방 전압과 단락 전류에서 바로 구하려면 먼저 thevenin_equivalent 를 쓴다."
    ),
    version="1.0.0",
)
def norton_equivalent(
    v_th: str,
    r_th: str,
) -> NortonEquivalentResult:
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
        "최대 전력 전달 정리로 최적 부하와 최대 전력을 구한다. R_L=R_th일 때 P_max=V_th²/(4R_th). "
        "v_th(V)와 r_th(Ω, 0 초과)는 Decimal 문자열. 반환: optimal_load(Ω), max_power(W). "
        "오용 주의: 이때 효율은 50%이므로 전력 효율이 중요한 전원 설계의 부하 선정 기준은 아니다."
    ),
    version="1.0.0",
)
def max_power_transfer(
    v_th: str,
    r_th: str,
) -> MaxPowerTransferResult:
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
