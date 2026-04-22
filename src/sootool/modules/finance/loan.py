"""Finance loan schedule tool.

공식 출처:
  원리금균등(EQUAL_PAYMENT): 표준 대출 상환 공식
    M = P * r_m * (1+r_m)^n / ((1+r_m)^n - 1)
    r_m = 월이자율 = annual_rate / 12

  원금균등(EQUAL_PRINCIPAL):
    매월 원금 = P / n
    매월 이자 = 잔액 * r_m

자료형: pure Decimal (ADR-008 finance = Decimal path)
반올림 정책: HALF_EVEN (기본), decimals=0 (원화 기본)

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, mul, power, sub
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy, apply

_VALID_METHODS = {"EQUAL_PAYMENT", "EQUAL_PRINCIPAL"}


def _parse_policy(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(f"유효하지 않은 반올림 정책: {rounding!r}") from exc


@REGISTRY.tool(
    namespace="finance",
    name="loan_schedule",
    description="대출 상환 스케줄 계산. 원리금균등(EQUAL_PAYMENT) 또는 원금균등(EQUAL_PRINCIPAL).",
    version="1.0.0",
)
def loan_schedule(
    principal: str,
    annual_rate: str,
    months: int,
    method: str = "EQUAL_PAYMENT",
    rounding: str = "HALF_EVEN",
    decimals: int = 0,
) -> dict[str, Any]:
    """Compute a loan amortization schedule.

    Args:
        principal:   원금 (Decimal string)
        annual_rate: 연 이자율 e.g. "0.03"
        months:      상환 기간 (개월)
        method:      "EQUAL_PAYMENT" (원리금균등) | "EQUAL_PRINCIPAL" (원금균등)
        rounding:    반올림 정책
        decimals:    소수점 자릿수 (원화 기본 0)

    Returns:
        {
            monthly_payment: str | None,  # None for EQUAL_PRINCIPAL
            schedule: [{month, payment, principal, interest, balance}],
            trace: dict,
        }
    """
    trace = CalcTrace(
        tool="finance.loan_schedule",
        formula=(
            "EQUAL_PAYMENT: M = P*r*(1+r)^n/((1+r)^n-1); "
            "EQUAL_PRINCIPAL: principal_per_month = P/n"
        ),
    )
    policy = _parse_policy(rounding)

    method = method.upper()
    if method not in _VALID_METHODS:
        raise InvalidInputError(
            f"method는 {sorted(_VALID_METHODS)} 중 하나여야 합니다. 입력값: {method!r}"
        )

    principal_d   = D(principal)
    annual_rate_d = D(annual_rate)

    if principal_d <= Decimal("0"):
        raise InvalidInputError("principal은 양수여야 합니다.")
    if annual_rate_d < Decimal("0"):
        raise InvalidInputError("annual_rate는 0 이상이어야 합니다.")
    if months <= 0:
        raise InvalidInputError("months는 1 이상이어야 합니다.")

    trace.input("principal",   principal)
    trace.input("annual_rate", annual_rate)
    trace.input("months",      months)
    trace.input("method",      method)
    trace.input("rounding",    rounding)
    trace.input("decimals",    decimals)

    monthly_rate = div(annual_rate_d, D("12"))
    trace.step("monthly_rate", str(monthly_rate))

    if method == "EQUAL_PAYMENT":
        return _equal_payment(principal_d, monthly_rate, months, policy, decimals, trace)
    else:
        return _equal_principal(principal_d, monthly_rate, months, policy, decimals, trace)


def _equal_payment(
    principal_d: Decimal,
    monthly_rate: Decimal,
    months: int,
    policy: RoundingPolicy,
    decimals: int,
    trace: CalcTrace,
) -> dict[str, Any]:
    """원리금균등 상환 스케줄."""
    n = D(str(months))

    if monthly_rate == Decimal("0"):
        # Zero-rate: equal payment = principal / months
        payment_raw = div(principal_d, n)
    else:
        # M = P * r * (1+r)^n / ((1+r)^n - 1)
        one_plus_r = add(Decimal("1"), monthly_rate)
        factor     = power(one_plus_r, months)
        numerator  = mul(principal_d, monthly_rate, factor)
        denom      = sub(factor, Decimal("1"))
        payment_raw = div(numerator, denom)

    monthly_payment = apply(payment_raw, decimals, policy)
    trace.step("monthly_payment_raw", str(payment_raw))
    trace.step("monthly_payment",     str(monthly_payment))

    schedule: list[dict[str, Any]] = []
    balance = principal_d

    for month in range(1, months + 1):
        interest_raw = mul(balance, monthly_rate)
        interest     = apply(interest_raw, decimals, policy)

        if month < months:
            payment          = monthly_payment
            principal_repaid = apply(sub(payment, interest), decimals, policy)
            balance          = sub(balance, principal_repaid)
        else:
            # Last payment: adjust so balance becomes exactly 0
            principal_repaid = balance
            payment          = apply(add(principal_repaid, interest), decimals, policy)
            balance          = Decimal("0")

        schedule.append({
            "month":     month,
            "payment":   str(payment),
            "principal": str(principal_repaid),
            "interest":  str(interest),
            "balance":   str(apply(balance, decimals, policy)),
        })

    trace.output({"rows": months, "monthly_payment": str(monthly_payment)})

    return {
        "monthly_payment": str(monthly_payment),
        "schedule":        schedule,
        "trace":           trace.to_dict(),
    }


def _equal_principal(
    principal_d: Decimal,
    monthly_rate: Decimal,
    months: int,
    policy: RoundingPolicy,
    decimals: int,
    trace: CalcTrace,
) -> dict[str, Any]:
    """원금균등 상환 스케줄."""
    n = D(str(months))
    principal_per_month = apply(div(principal_d, n), decimals, policy)
    trace.step("principal_per_month", str(principal_per_month))

    schedule: list[dict[str, Any]] = []
    balance = principal_d

    for month in range(1, months + 1):
        interest_raw = mul(balance, monthly_rate)
        interest     = apply(interest_raw, decimals, policy)

        if month < months:
            principal_repaid = principal_per_month
        else:
            # Last month: repay remaining balance
            principal_repaid = balance

        payment = apply(add(principal_repaid, interest), decimals, policy)
        balance = sub(balance, principal_repaid)

        schedule.append({
            "month":     month,
            "payment":   str(payment),
            "principal": str(principal_repaid),
            "interest":  str(interest),
            "balance":   str(apply(balance, decimals, policy)),
        })

    trace.output({"rows": months})

    return {
        "monthly_payment": None,
        "schedule":        schedule,
        "trace":           trace.to_dict(),
    }
