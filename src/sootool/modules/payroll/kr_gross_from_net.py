"""Net monthly pay -> gross monthly pay (reverse of payroll.kr_salary).

Author: 최진호
Date: 2026-10-03

  1. kr_salary(월급) 의 실수령액(net)은 월급에 대해 단조 증가하는 계단 함수다(구간별 세율, 원 단위 절사).
  2. 실수령액이 목표 이상이 되는 가장 작은 월급(원 단위)을 이분법으로 찾는다(core.solver).
  3. 계단 함수라 같은 실수령액이 되는 월급이 여러 개일 수 있고 어떤 월급으로도 정확히 만들 수 없는
     실수령액도 있다. 그래서 목표 이상을 처음 만족하는 월급을 반환하고 달성한 실수령액과 차이(residual)를 함께
     알린다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.core.solver import smallest_integer_satisfying
from sootool.modules.payroll.kr_salary import payroll_kr_salary

_UPPER_FACTOR = Decimal(3)   # 소득세 최고세율과 4대보험을 합쳐도 세전 월급은 세후의 3배를 넘지 않는다.


@REGISTRY.tool(
    namespace="payroll",
    name="kr_gross_from_net",
    description=(
        "역산: 세후 월급(net_monthly)에서 세전 월급을 구한다. payroll.kr_salary 의 계단형 실수령액이 목표 이상이 "
        "되는 가장 작은 월급(원 단위)을 이분법으로 찾고, 달성한 실수령액과 차이(residual)를 함께 반환한다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_gross_from_net(
    net_monthly:    str,
    year:           int,
    meal_allowance: str = "0",
    num_dependents: int = 1,
) -> dict[str, Any]:
    """Find the gross monthly salary whose net pay equals ``net_monthly``.

    Returns:
        {net_target, gross, achieved_net, residual, exact, evaluations, salary, trace}
        ``gross`` is the smallest whole-won salary whose net pay is at least ``net_monthly``;
        ``salary`` is the full payroll.kr_salary result at ``gross``.
    """
    trace = CalcTrace(
        tool="payroll.kr_gross_from_net",
        formula="find gross such that payroll.kr_salary(gross).net = net_monthly (integer bisection)",
    )
    target = D(net_monthly)
    if target <= 0:
        raise DomainConstraintError("net_monthly 는 0 보다 커야 합니다.")

    def net_reaches_target(gross: int) -> bool:
        salary = payroll_kr_salary(
            monthly_salary=str(gross), year=year, meal_allowance=meal_allowance, num_dependents=num_dependents,
        )
        return D(salary["net"]) >= target

    lower = int(target.to_integral_value(rounding="ROUND_CEILING"))
    upper = int((target * _UPPER_FACTOR).to_integral_value(rounding="ROUND_CEILING"))
    gross_int, evaluations = smallest_integer_satisfying(net_reaches_target, lower, upper)
    gross  = str(gross_int)
    salary = payroll_kr_salary(
        monthly_salary=gross, year=year, meal_allowance=meal_allowance, num_dependents=num_dependents,
    )
    residual = D(salary["net"]) - target

    trace.input("net_monthly",    net_monthly)
    trace.input("year",           year)
    trace.input("meal_allowance", meal_allowance)
    trace.input("num_dependents", num_dependents)
    trace.step("gross",        gross)
    trace.step("evaluations",  evaluations)
    trace.output(gross)

    response = {
        "net_target":   net_monthly,
        "gross":        gross,
        "achieved_net": salary["net"],
        "residual":     str(residual),
        "exact":        residual == 0,
        "evaluations":  evaluations,
        "salary":       {k: v for k, v in salary.items() if k != "_meta"},
        "trace":        trace.to_dict(),
    }
    for key in ("policy_source", "policy_sha256", "policy_effective_date", "policy_effective_to",
                "policy_status", "policy_citations", "policy_audit_id"):
        if key in salary:
            response[key] = salary[key]
    return response
