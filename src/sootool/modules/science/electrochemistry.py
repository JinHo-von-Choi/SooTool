"""Electrochemistry: Nernst equation, Faraday electrolysis, battery capacity.

내부 자료형 (ADR-008):
- Nernst: Decimal 입력, ln(Q)는 mpmath → Decimal.
- Faraday: 전 구간 Decimal (정수/실수 분수).
- 배터리: 전 구간 Decimal.

물리 상수:
- R = 8.314462618 J/(mol·K)
- F = 96485.33212 C/mol
- T 기본 298.15 K (25°C)

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import threading
from decimal import Decimal

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_R = D("8.314462618")    # J/(mol·K)
_F = D("96485.33212")    # C/mol
_MPDPS = 40
_MP_LOCK = threading.Lock()


class NernstResult(TracedResult):
    e:           str
    unit:        str
    coefficient: str


class FaradayElectrolysisResult(TracedResult):
    mass_g: str


class BatteryCapacityResult(TracedResult):
    result: str
    unit:   str


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) Decimal 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="science",
    name="nernst",
    description=(
        "Nernst 방정식으로 비표준 조건의 전극 전위를 V 단위로 계산한다. E = E0 - (RT / nF) * ln(Q). "
        "e0(V)와 reaction_q(양수)는 Decimal 문자열, n은 양의 정수 전자수, temperature는 켈빈(기본 298.15). "
        "R=8.314462618, F=96485.33212를 쓰고 결과는 소수 20자리로 맞춘다. "
        "섭씨 온도를 그대로 넣거나 Q 대신 ln(Q)를 넣으면 안 된다."
    ),
    version="1.0.0",
)
def nernst(
    e0:           str,
    n:            int,
    reaction_q:   str,
    temperature:  str = "298.15",
) -> NernstResult:
    """Compute electrode potential via the Nernst equation."""
    trace = CalcTrace(
        tool="science.nernst",
        formula="E = E0 - (R T / n F) * ln(Q)",
    )
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise InvalidInputError(f"n은 양의 정수여야 합니다: {n!r}")
    e0_d  = _parse_decimal(e0,          "e0")
    q_d   = _parse_decimal(reaction_q,  "reaction_q")
    t_d   = _parse_decimal(temperature, "temperature")

    if q_d <= D("0"):
        raise DomainConstraintError(f"reaction_q는 양수여야 합니다: {reaction_q}")
    if t_d <= D("0"):
        raise DomainConstraintError(f"temperature(K)는 양수여야 합니다: {temperature}")

    trace.input("e0", e0)
    trace.input("n", n)
    trace.input("reaction_q", reaction_q)
    trace.input("temperature", temperature)

    coef = _R * t_d / (D(n) * _F)
    with _MP_LOCK, mpmath.workdps(_MPDPS):
        ln_q_mpf = mpmath.log(mpmath.mpf(str(q_d)))
        ln_q_dec = mpmath_to_decimal(ln_q_mpf, digits=25)
    delta = coef * ln_q_dec
    e     = e0_d - delta
    # Quantize to 20 digits for deterministic output length across threads.
    e     = e.quantize(Decimal("1E-20"))
    e_str = str(e)

    trace.step("coefficient_RT/nF", str(coef))
    trace.step("ln_Q",              str(ln_q_dec))
    trace.step("delta",             str(delta))
    trace.step("E",                 e_str)
    trace.output({"e": e_str})

    return {
        "e":           e_str,
        "unit":        "V",
        "coefficient": str(coef),
        "trace":       trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="science",
    name="faraday_electrolysis",
    description=(
        "패러데이 법칙으로 전기분해 시 석출되는 질량(g)을 계산한다. m = (I * t * M) / (n * F). "
        "current_a는 암페어, time_s는 초, molar_mass_g는 g/mol(모두 양수 Decimal 문자열), n_electrons는 양의 정수. "
        "F=96485.33212 C/mol이며 반올림하지 않는다. 시간을 분이나 시간 단위로 넣으면 안 되고 전류 효율은 100%로 가정한다."
    ),
    version="1.0.0",
)
def faraday_electrolysis(
    current_a:        str,
    time_s:           str,
    molar_mass_g:     str,
    n_electrons:      int,
) -> FaradayElectrolysisResult:
    """Compute deposited mass via Faraday's laws of electrolysis."""
    trace = CalcTrace(
        tool="science.faraday_electrolysis",
        formula="m = I * t * M / (n * F)",
    )
    if not isinstance(n_electrons, int) or isinstance(n_electrons, bool) or n_electrons <= 0:
        raise InvalidInputError(f"n_electrons는 양의 정수여야 합니다: {n_electrons!r}")

    i = _parse_decimal(current_a,    "current_a")
    t = _parse_decimal(time_s,       "time_s")
    m_molar = _parse_decimal(molar_mass_g, "molar_mass_g")
    if i <= D("0") or t <= D("0") or m_molar <= D("0"):
        raise DomainConstraintError("current/time/molar_mass는 양수여야 합니다.")

    trace.input("current_a",    current_a)
    trace.input("time_s",       time_s)
    trace.input("molar_mass_g", molar_mass_g)
    trace.input("n_electrons",  n_electrons)

    m = (i * t * m_molar) / (D(n_electrons) * _F)
    m_str = str(m)
    trace.step("mass_g", m_str)
    trace.output({"mass_g": m_str})

    return {"mass_g": m_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="science",
    name="battery_capacity",
    description=(
        "배터리 용량을 Ah와 Wh 사이에서 변환한다. Wh = Ah * V, Ah = Wh / V. "
        "mode='ah_to_wh'(기본) 또는 'wh_to_ah', value는 0 이상, voltage는 양수(V)이며 Decimal 문자열이다. "
        "나눗셈은 반올림하지 않는다. 직렬이나 병렬 구성 용량은 계산하지 않으므로 팩 전체 전압과 용량을 쌍으로 넣어야 한다."
    ),
    version="1.0.0",
)
def battery_capacity(
    value:    str,
    voltage:  str,
    mode:     str = "ah_to_wh",
) -> BatteryCapacityResult:
    """Convert battery capacity between Ah and Wh."""
    trace = CalcTrace(
        tool="science.battery_capacity",
        formula="Wh = Ah * V, Ah = Wh / V",
    )
    v = _parse_decimal(voltage, "voltage")
    if v <= D("0"):
        raise DomainConstraintError(f"voltage는 양수여야 합니다: {voltage}")
    x = _parse_decimal(value, "value")
    if x < D("0"):
        raise DomainConstraintError(f"value는 음수가 될 수 없습니다: {value}")

    trace.input("value", value)
    trace.input("voltage", voltage)
    trace.input("mode", mode)

    if mode == "ah_to_wh":
        out  = x * v
        unit = "Wh"
    elif mode == "wh_to_ah":
        out  = x / v
        unit = "Ah"
    else:
        raise InvalidInputError(f"mode는 'ah_to_wh'|'wh_to_ah' 여야 합니다: {mode!r}")

    out_str = str(out)
    trace.step(f"result_{unit}", out_str)
    trace.output({"result": out_str, "unit": unit})

    return {"result": out_str, "unit": unit, "trace": trace.to_dict()}
