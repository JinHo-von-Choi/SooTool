"""Hourly wage -> monthly net pay converter.

Author: 최진호
Date: 2026-04-24

  1. 월급여 = 시급 * 월 환산시간 (주 40시간 법정근로 기준 209시간)
  2. 주휴수당 포함 209h (주 40h * 4.345주 + 주휴 8h * 4.345주 ≈ 209h)
  3. kr_salary 호출하여 실수령액 도출
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.payroll.kr_salary import payroll_kr_salary

DEFAULT_MONTHLY_HOURS = Decimal("209")  # 주 40h 법정 기준


@REGISTRY.tool(
    namespace="payroll",
    name="hourly_to_monthly_net",
    description=(
        "시급 → 월급(주 40h, 월 209h 환산) → 실수령액. "
        "kr_salary와 연계하여 4대보험·세액 공제 반영."
    ),
    version="1.0.0",
)
def payroll_hourly_to_monthly_net(
    hourly_wage:    str,
    year:           int,
    monthly_hours:  str  = "209",
    meal_allowance: str  = "0",
    num_dependents: int  = 1,
) -> dict[str, Any]:
    """Convert an hourly wage to monthly gross and net pay.

    Args:
        hourly_wage:    시급(원/시간)
        year:           과세연도
        monthly_hours:  월 환산시간 (기본 209, 주 40h + 주휴 환산)
        meal_allowance: 월 식대(원, 비과세 한도까지만 공제)
        num_dependents: 부양가족 수(본인 포함)

    Returns:
        {hourly_wage, monthly_hours, monthly_gross, net, insurances, taxes,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.hourly_to_monthly_net",
        formula=(
            "월급 = 시급 * 월환산시간; "
            "net = payroll.kr_salary(월급, year, meal_allowance, num_dependents)"
        ),
    )

    wage   = D(hourly_wage)
    hours  = D(monthly_hours)

    if wage <= Decimal("0"):
        raise InvalidInputError("hourly_wage는 0보다 커야 합니다.")
    if hours <= Decimal("0"):
        raise InvalidInputError("monthly_hours는 0보다 커야 합니다.")
    if num_dependents < 1:
        raise InvalidInputError("num_dependents는 1 이상이어야 합니다.")

    trace.input("hourly_wage",    hourly_wage)
    trace.input("year",           year)
    trace.input("monthly_hours",  monthly_hours)
    trace.input("meal_allowance", meal_allowance)
    trace.input("num_dependents", num_dependents)

    monthly_gross_raw = wage * hours
    monthly_gross     = round_apply(monthly_gross_raw, 0, RoundingPolicy.DOWN)

    salary_resp = payroll_kr_salary(
        monthly_salary = str(monthly_gross),
        year           = year,
        meal_allowance = meal_allowance,
        num_dependents = num_dependents,
    )

    trace.step("monthly_gross",       str(monthly_gross))
    trace.step("kr_salary_trace",     salary_resp["trace"])
    trace.output(salary_resp["net"])

    resp: dict[str, Any] = {
        "hourly_wage":    str(wage),
        "monthly_hours":  str(hours),
        "monthly_gross":  str(monthly_gross),
        "taxable":        salary_resp["taxable"],
        "net":            salary_resp["net"],
        "insurances":     salary_resp["insurances"],
        "taxes":          salary_resp["taxes"],
        "policy_version": salary_resp["policy_version"],
        "trace":          trace.to_dict(),
    }
    # Propagate policy_source/etc. from the delegated call if present
    for key in (
        "policy_source", "policy_audit_id",
        "policy_sha256", "policy_effective_date",
    ):
        if key in salary_resp:
            resp[key] = salary_resp[key]
    if "_meta" in salary_resp:
        resp["_meta"] = salary_resp["_meta"]
    return resp
