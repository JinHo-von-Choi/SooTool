"""Finance TVM tools: Present Value and Future Value.

공식 출처: Brealey, Myers & Allen, "Principles of Corporate Finance", 13th ed.
  PV = FV / (1 + r)^n
  FV = PV * (1 + r)^n

자료형: pure Decimal (ADR-008 finance = Decimal path)
반올림 정책: HALF_EVEN (기본) — 금융 계산 표준

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, power
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy, apply


def _parse_policy(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(f"유효하지 않은 반올림 정책: {rounding!r}") from exc


def _validate_rate(rate_d: Decimal) -> None:
    if rate_d < Decimal("0"):
        raise InvalidInputError("rate는 0 이상이어야 합니다.")


def _validate_periods(periods: int) -> None:
    if periods <= 0:
        raise InvalidInputError("periods는 1 이상이어야 합니다.")


@REGISTRY.tool(
    namespace="finance",
    name="pv",
    description="현재가치(Present Value) 계산. PV = FV / (1+r)^n",
    version="1.0.0",
)
def pv(
    future_value: str,
    rate: str,
    periods: int,
    rounding: str = "HALF_EVEN",
    decimals: int = 2,
) -> dict[str, Any]:
    """Compute the present value of a future cash flow.

    Args:
        future_value: 미래가치 (Decimal string)
        rate:         기간별 이자율 e.g. "0.05"
        periods:      기간 수
        rounding:     반올림 정책
        decimals:     반올림 소수점 자릿수

    Returns:
        {pv: str, trace: dict}
    """
    trace = CalcTrace(
        tool="finance.pv",
        formula="PV = FV / (1 + r)^n",
    )
    policy = _parse_policy(rounding)

    fv_d   = D(future_value)
    rate_d = D(rate)
    _validate_rate(rate_d)
    _validate_periods(periods)

    trace.input("future_value", future_value)
    trace.input("rate",         rate)
    trace.input("periods",      periods)
    trace.input("rounding",     rounding)
    trace.input("decimals",     decimals)

    one_plus_r = add(Decimal("1"), rate_d)
    trace.step("(1+r)", str(one_plus_r))

    discount_factor = power(one_plus_r, periods)
    trace.step("(1+r)^n", str(discount_factor))

    pv_raw = div(fv_d, discount_factor)
    trace.step("pv_raw", str(pv_raw))

    pv_val = apply(pv_raw, decimals, policy)
    trace.output(str(pv_val))

    return {
        "pv":    str(pv_val),
        "trace": trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="fv",
    description="미래가치(Future Value) 계산. FV = PV * (1+r)^n",
    version="1.0.0",
)
def fv(
    present_value: str,
    rate: str,
    periods: int,
    rounding: str = "HALF_EVEN",
    decimals: int = 2,
) -> dict[str, Any]:
    """Compute the future value of a present cash flow.

    Args:
        present_value: 현재가치 (Decimal string)
        rate:          기간별 이자율 e.g. "0.05"
        periods:       기간 수
        rounding:      반올림 정책
        decimals:      반올림 소수점 자릿수

    Returns:
        {fv: str, trace: dict}
    """
    trace = CalcTrace(
        tool="finance.fv",
        formula="FV = PV * (1 + r)^n",
    )
    policy = _parse_policy(rounding)

    pv_d   = D(present_value)
    rate_d = D(rate)
    _validate_rate(rate_d)
    _validate_periods(periods)

    trace.input("present_value", present_value)
    trace.input("rate",          rate)
    trace.input("periods",       periods)
    trace.input("rounding",      rounding)
    trace.input("decimals",      decimals)

    one_plus_r     = add(Decimal("1"), rate_d)
    growth_factor  = power(one_plus_r, periods)
    trace.step("(1+r)",   str(one_plus_r))
    trace.step("(1+r)^n", str(growth_factor))

    fv_raw = pv_d * growth_factor
    trace.step("fv_raw", str(fv_raw))

    fv_val = apply(fv_raw, decimals, policy)
    trace.output(str(fv_val))

    return {
        "fv":    str(fv_val),
        "trace": trace.to_dict(),
    }
