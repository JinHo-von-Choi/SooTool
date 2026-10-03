"""Net monthly pay -> gross monthly pay (reverse of payroll.kr_salary).

Author: 최진호
Date: 2026-10-03

  1. kr_salary(월급) 의 공제 합계 C(월급) = 4대보험 + 소득세 + 지방소득세 는 월급에 대해 단조 비감소다.
     간이세액표 세액은 월급여액에 대해 비감소이고 보험료도 끝수 버림과 상·하한을 거쳐 비감소다.
  2. 실수령액 net(월급) = 월급 - C(월급) 은 단조가 아니다. 간이세액표 행 경계와 국민연금 천원 단위 경계에서
     공제액이 계단처럼 뛰어 월급 1원 증가에 실수령액이 줄 수 있다. 따라서 이분법은 최솟값을 보장하지 못한다.
  3. 목표 실수령액 T 를 만족하는 정수 월급 g 의 조건은 g >= T + C(g) 이다. g_0 = max(ceil(T), ceil(식대)) 에서
     g_{k+1} = ceil(T + C(g_k)) 를 반복하면 수열은 비감소이고 조건을 만족하는 가장 작은 월급 g* 를 넘지 않는다
     (C 비감소, g_k <= g* 이면 g_{k+1} <= ceil(T + C(g*)) <= g*). 정수 수열이므로 유한 번에 고정점에 닿고,
     고정점은 조건을 만족하므로 곧 g* 다.
  4. 같은 실수령액이 되는 월급이 여러 개일 수 있고 어떤 월급으로도 정확히 만들 수 없는 실수령액도 있다.
     그래서 목표 이상을 처음 만족하는 월급을 반환하고 달성한 실수령액과 차이(residual)를 함께 알린다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.modules.payroll.kr_salary import KrSalaryResult, payroll_kr_salary

_MAX_ITERATIONS = 1000   # 공제 합계의 월급 대비 증가율은 1 미만이라 실제 반복은 수십 회 이내다.


class KrGrossFromNetResult(PolicyResult):
    net_target:   str
    gross:        str
    achieved_net: str
    residual:     str
    exact:        bool
    evaluations:  int
    salary:       KrSalaryResult


def _ceil_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding="ROUND_CEILING"))


@REGISTRY.tool(
    namespace="payroll",
    name="kr_gross_from_net",
    description=(
        "역산: 세후 월급(net_monthly, 원 문자열)에서 세전 월급을 구한다. payroll.kr_salary 의 실수령액이 목표 이상이 되는 "
        "가장 작은 정수 월급을 공제 합계의 고정점 반복으로 찾고, 달성한 실수령액과 차이(residual)를 함께 반환한다. "
        "정확히 같은 실수령액이 불가능한 목표도 있으니 exact 를 확인하고, 연봉이 아닌 월 단위 실수령액을 넣어야 한다."
    ),
    version="2.0.0",
    policy=True,
)
def payroll_kr_gross_from_net(
    net_monthly:    str,
    year:           int,
    meal_allowance: str = "0",
    num_dependents: int = 1,
    children_8_20:  int = 0,
) -> KrGrossFromNetResult:
    """Find the gross monthly salary whose net pay equals ``net_monthly``.

    Returns:
        {net_target, gross, achieved_net, residual, exact, evaluations, salary, trace}
        ``gross`` is the smallest whole-won salary whose net pay is at least ``net_monthly``;
        ``salary`` is the full payroll.kr_salary result at ``gross``.
    """
    trace = CalcTrace(
        tool="payroll.kr_gross_from_net",
        formula=(
            "gross = min{g : g - C(g) >= net_monthly}, C = 4대보험 + 소득세 + 지방소득세 (비감소); "
            "g_{k+1} = ceil(net_monthly + C(g_k)) 고정점 반복"
        ),
    )
    target = D(net_monthly)
    if target <= 0:
        raise DomainConstraintError("net_monthly 는 0 보다 커야 합니다.")

    def salary_at(gross: int) -> KrSalaryResult:
        result: KrSalaryResult = payroll_kr_salary(
            monthly_salary=str(gross), year=year, meal_allowance=meal_allowance,
            num_dependents=num_dependents, children_8_20=children_8_20,
        )
        return result

    gross_int   = max(_ceil_int(target), _ceil_int(D(meal_allowance)))
    salary      = salary_at(gross_int)
    evaluations = 1
    while True:
        deductions = D(salary["insurances"]["total"]) + D(salary["taxes"]["total"])
        following  = _ceil_int(target + deductions)
        if following <= gross_int:
            break
        if evaluations >= _MAX_ITERATIONS:
            raise DomainConstraintError("세전 월급 역산이 반복 한도 안에 수렴하지 않았습니다.")
        gross_int   = following
        salary      = salary_at(gross_int)
        evaluations += 1

    gross    = str(gross_int)
    residual = D(salary["net"]) - target

    trace.input("net_monthly",    net_monthly)
    trace.input("year",           year)
    trace.input("meal_allowance", meal_allowance)
    trace.input("num_dependents", num_dependents)
    trace.input("children_8_20",  children_8_20)
    trace.step("gross",        gross)
    trace.step("evaluations",  evaluations)
    trace.output(gross)

    response: dict[str, Any] = {
        "net_target":   net_monthly,
        "gross":        gross,
        "achieved_net": salary["net"],
        "residual":     str(residual),
        "exact":        residual == 0,
        "evaluations":  evaluations,
        "salary":       cast(KrSalaryResult, {k: v for k, v in salary.items() if k != "_meta"}),
        "trace":        trace.to_dict(),
    }
    for key in ("policy_version", "policy_source", "policy_sha256", "policy_effective_date",
                "policy_effective_to", "policy_status", "policy_citations", "policy_audit_id"):
        if key in salary:
            response[key] = salary[key]
    return cast(KrGrossFromNetResult, response)
