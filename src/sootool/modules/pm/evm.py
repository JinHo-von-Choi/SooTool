"""PM Earned Value Management (EVM) tool.

내부 자료형: 전 구간 Decimal.
SPI = EV / PV  (Schedule Performance Index)
CPI = EV / AC  (Cost Performance Index)
SV  = EV - PV  (Schedule Variance)
CV  = EV - AC  (Cost Variance)
EAC = BAC / CPI  (Estimate at Completion)
ETC = EAC - AC  (Estimate to Complete)
VAC = BAC - EAC  (Variance at Completion)

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="pm",
    name="evm",
    description=(
        "획득 가치 분석(EVM): SPI, CPI, SV, CV, EAC, ETC, VAC 계산. "
        "전 구간 Decimal 정밀 연산."
    ),
    version="1.0.0",
)
def evm(
    pv: str,
    ev: str,
    ac: str,
    bac: str,
) -> dict[str, Any]:
    """Compute Earned Value Management metrics.

    Args:
        pv:  Planned Value — budgeted cost of scheduled work (Decimal string).
        ev:  Earned Value  — budgeted cost of work performed (Decimal string).
        ac:  Actual Cost   — actual cost of work performed (Decimal string).
        bac: Budget at Completion — total approved budget (Decimal string, positive).

    Returns:
        {spi, cpi, sv, cv, eac, etc_, vac, trace}

    Raises:
        DomainConstraintError: If pv=0 (SPI division) or ac=0 (CPI division) or bac<=0.
        InvalidInputError:     On non-numeric inputs.
    """
    trace = CalcTrace(
        tool="pm.evm",
        formula=(
            "SPI=EV/PV, CPI=EV/AC, SV=EV-PV, CV=EV-AC, "
            "EAC=BAC/CPI, ETC=EAC-AC, VAC=BAC-EAC"
        ),
    )

    d_pv  = _parse_decimal(pv,  "pv")
    d_ev  = _parse_decimal(ev,  "ev")
    d_ac  = _parse_decimal(ac,  "ac")
    d_bac = _parse_decimal(bac, "bac")

    if d_bac <= D("0"):
        raise DomainConstraintError(f"bac는 양수여야 합니다: {bac}")
    if d_pv == D("0"):
        raise DomainConstraintError("pv가 0이면 SPI를 계산할 수 없습니다 (0으로 나눔).")
    if d_ac == D("0"):
        raise DomainConstraintError("ac가 0이면 CPI를 계산할 수 없습니다 (0으로 나눔).")

    trace.input("pv",  str(d_pv))
    trace.input("ev",  str(d_ev))
    trace.input("ac",  str(d_ac))
    trace.input("bac", str(d_bac))

    spi  = d_ev / d_pv
    cpi  = d_ev / d_ac
    sv   = d_ev - d_pv
    cv   = d_ev - d_ac
    eac  = d_bac / cpi
    etc_ = eac - d_ac
    vac  = d_bac - eac

    trace.step("SPI = EV/PV",    str(spi))
    trace.step("CPI = EV/AC",    str(cpi))
    trace.step("SV  = EV-PV",    str(sv))
    trace.step("CV  = EV-AC",    str(cv))
    trace.step("EAC = BAC/CPI",  str(eac))
    trace.step("ETC = EAC-AC",   str(etc_))
    trace.step("VAC = BAC-EAC",  str(vac))

    result = {
        "spi":   str(spi),
        "cpi":   str(cpi),
        "sv":    str(sv),
        "cv":    str(cv),
        "eac":   str(eac),
        "etc_":  str(etc_),
        "vac":   str(vac),
        "trace": trace.to_dict(),
    }
    trace.output({k: v for k, v in result.items() if k != "trace"})
    return result
