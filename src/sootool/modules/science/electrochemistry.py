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
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_R = D("8.314462618")    # J/(mol·K)
_F = D("96485.33212")    # C/mol
_MPDPS = 40
_MP_LOCK = threading.Lock()


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) Decimal 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="science",
    name="nernst",
    description=(
        "Nernst 방정식: E = E0 - (RT / nF) * ln(Q). "
        "E0 표준 전극전위(V), n 전자수, Q 반응지수, T 온도(K, 기본 298.15)."
    ),
    version="1.0.0",
)
def nernst(
    e0:           str,
    n:            int,
    reaction_q:   str,
    temperature:  str = "298.15",
) -> dict[str, Any]:
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
        "패러데이 전기분해 법칙: m = (I * t * M) / (n * F). "
        "I 전류(A), t 시간(s), M 몰질량(g/mol), n 전자수. 결과 m은 g."
    ),
    version="1.0.0",
)
def faraday_electrolysis(
    current_a:        str,
    time_s:           str,
    molar_mass_g:     str,
    n_electrons:      int,
) -> dict[str, Any]:
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
        "배터리 용량 변환. Ah↔Wh: Wh = Ah * V. "
        "mode='ah_to_wh' 또는 'wh_to_ah'. voltage는 V 단위."
    ),
    version="1.0.0",
)
def battery_capacity(
    value:    str,
    voltage:  str,
    mode:     str = "ah_to_wh",
) -> dict[str, Any]:
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
