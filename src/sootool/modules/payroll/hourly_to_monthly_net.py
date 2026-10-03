"""Hourly wage -> monthly net pay converter.

Author: 최진호
Date: 2026-04-24
Modified: 2026-10-03

  1. 월급여 = 시급 * 월 환산시간 (주 40시간 법정근로 기준 209시간)
  2. 주휴수당 포함 209h (주 40h * 4.345주 + 주휴 8h * 4.345주 ≈ 209h)
  3. kr_salary 호출하여 실수령액 도출
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.payroll.kr_salary import (
    SalaryInsurances,
    SalaryTaxes,
    payroll_kr_salary,
)

DEFAULT_MONTHLY_HOURS = Decimal("209")  # 주 40h 법정 기준


class HourlyToMonthlyNetResult(PolicyResult):
    hourly_wage:   str
    monthly_hours: str
    monthly_gross: str
    taxable:       str
    net:           str
    insurances:    SalaryInsurances
    taxes:         SalaryTaxes


@REGISTRY.tool(
    namespace="payroll",
    name="hourly_to_monthly_net",
    description=(
        "시급(원, 문자열)을 월 환산시간(기본 209시간, 주 40시간과 주휴 포함)에 곱해 월급으로 바꾸고 원 미만을 버린 뒤 "
        "payroll.kr_salary 로 4대보험과 간이세액표 소득세를 공제한 실수령액을 구한다. 식대 비과세 한도, 공제대상가족 수, "
        "8~20세 자녀 수(children_8_20)를 받는다. 주 40시간이 아닌 근로는 monthly_hours 를 직접 줘야 한다."
    ),
    version="1.1.0",
    policy=True,
)
def payroll_hourly_to_monthly_net(
    hourly_wage:    str,
    year:           int,
    monthly_hours:  str  = "209",
    meal_allowance: str  = "0",
    num_dependents: int  = 1,
    children_8_20:  int  = 0,
) -> HourlyToMonthlyNetResult:
    """Convert an hourly wage to monthly gross and net pay.

    Args:
        hourly_wage:    시급(원/시간)
        year:           과세연도
        monthly_hours:  월 환산시간 (기본 209, 주 40h + 주휴 환산)
        meal_allowance: 월 식대(원, 비과세 한도까지만 공제)
        num_dependents: 간이세액표 공제대상가족 수(본인 포함)
        children_8_20:  공제대상가족 중 8세 이상 20세 이하 자녀 수(기본 0)

    Returns:
        {hourly_wage, monthly_hours, monthly_gross, taxable, net, insurances, taxes,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.hourly_to_monthly_net",
        formula=(
            "월급 = 시급 * 월환산시간; "
            "net = payroll.kr_salary(월급, year, meal_allowance, num_dependents, children_8_20)"
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
    trace.input("children_8_20",  children_8_20)

    monthly_gross_raw = wage * hours
    monthly_gross     = round_apply(monthly_gross_raw, 0, RoundingPolicy.DOWN)

    salary_resp = payroll_kr_salary(
        monthly_salary = str(monthly_gross),
        year           = year,
        meal_allowance = meal_allowance,
        num_dependents = num_dependents,
        children_8_20  = children_8_20,
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
        "policy_source", "policy_audit_id", "policy_sha256",
        "policy_effective_date", "policy_effective_to",
        "policy_status", "policy_citations",
    ):
        if key in salary_resp:
            resp[key] = salary_resp[key]
    if "_meta" in salary_resp:
        resp["_meta"] = salary_resp["_meta"]
    return cast(HourlyToMonthlyNetResult, resp)
