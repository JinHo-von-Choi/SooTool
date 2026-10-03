"""Korean bonus withholding tax (상여 세액) calculator.

Author: 최진호
Date: 2026-04-24
Modified: 2026-10-03

상여 원천징수세액은 근로소득 간이세액표(소득세법 시행령 별표 2)로 계산한다.

  method="averaging" (소득세법 제136조제1항제1호):
    - 상여 / 지급대상기간 월수 + 월급여 를 합산한 금액의 간이세액 x 월수
      - 그 기간 상여 외 급여에 대해 원천징수한 세액(월급여 간이세액 x 월수)
  method="simple":
    - (월급여 + 상여) 간이세액 - 월급여 간이세액 (지급대상기간 1개월로 본 값)

base_annual_tax, combined_annual_tax 는 각 월 간이세액의 12배(연 환산 원천징수액)다.
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
from sootool.modules.tax.kr_withholding import monthly_withholding_tax
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_VALID_METHODS = {"simple", "averaging"}


class KrBonusTaxResult(PolicyResult):
    bonus:                 str
    monthly_salary:        str
    method:                str
    payment_period_months: int
    base_monthly_tax:      str
    combined_monthly_tax:  str
    base_annual_tax:       str
    combined_annual_tax:   str
    bonus_tax:             str


@REGISTRY.tool(
    namespace="payroll",
    name="kr_bonus_tax",
    description=(
        "상여금 원천징수세액을 근로소득 간이세액표로 구한다. method=averaging(기본, 소득세법 제136조제1항제1호)은 "
        "상여를 지급대상기간 월수(1~12, 기본 12)로 안분해 월급여에 더한 간이세액에서 월급여 간이세액을 빼고 월수를 곱하며, "
        "simple 은 1개월분으로 본다. 금액은 원 문자열이고 세액은 원 미만 버림이다. 비과세 상여는 빼고 넣어야 한다."
    ),
    version="2.0.0",
    policy=True,
)
def payroll_kr_bonus_tax(
    bonus_amount:          str,
    monthly_salary:        str,
    year:                  int,
    dependents:            int = 1,
    method:                str = "averaging",
    payment_period_months: int = 12,
    children_8_20:         int = 0,
) -> KrBonusTaxResult:
    """Calculate withholding tax on a Korean bonus payment.

    Args:
        bonus_amount:          상여금(원, 세전, 비과세 제외)
        monthly_salary:        상여 외 월평균 급여액(원, 비과세 제외)
        year:                  귀속연도
        dependents:            간이세액표 공제대상가족 수(본인 포함)
        method:                "simple" | "averaging"
        payment_period_months: 지급대상기간 월수(averaging, 1~12)
        children_8_20:         공제대상가족 중 8세 이상 20세 이하 자녀 수(기본 0)

    Returns:
        {bonus, monthly_salary, method, payment_period_months,
         base_monthly_tax, combined_monthly_tax, base_annual_tax, combined_annual_tax,
         bonus_tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_bonus_tax",
        formula=(
            "averaging: 간이세액(월급여 + 상여/월수) * 월수 - 간이세액(월급여) * 월수; "
            "simple: 간이세액(월급여 + 상여) - 간이세액(월급여)"
        ),
    )

    if method not in _VALID_METHODS:
        raise InvalidInputError(
            f"method는 {sorted(_VALID_METHODS)} 중 하나여야 합니다."
        )
    if dependents < 1:
        raise InvalidInputError("dependents는 1 이상이어야 합니다 (본인 포함).")
    if payment_period_months < 1 or payment_period_months > 12:
        raise InvalidInputError(
            "payment_period_months는 1~12 범위여야 합니다."
        )

    bonus   = D(bonus_amount)
    monthly = D(monthly_salary)

    if bonus < Decimal("0"):
        raise InvalidInputError("bonus_amount는 0 이상이어야 합니다.")
    if monthly < Decimal("0"):
        raise InvalidInputError("monthly_salary는 0 이상이어야 합니다.")

    wh_doc  = policy_load("tax", "kr_withholding", year)
    wh_data = wh_doc["data"]
    pv      = wh_doc["policy_version"]

    trace.input("bonus_amount",          bonus_amount)
    trace.input("monthly_salary",        monthly_salary)
    trace.input("year",                  year)
    trace.input("dependents",            dependents)
    trace.input("method",                method)
    trace.input("payment_period_months", payment_period_months)
    trace.input("children_8_20",         children_8_20)
    trace.input("policy_version",        pv)

    def table_tax(salary: Decimal) -> Decimal:
        return monthly_withholding_tax(salary, dependents, children_8_20, wh_data)

    months   = Decimal(payment_period_months) if method == "averaging" else Decimal("1")
    combined = monthly + bonus / months
    base_tax = table_tax(monthly)
    comb_tax = table_tax(combined)
    raw_tax  = (comb_tax - base_tax) * months

    if raw_tax < Decimal("0"):
        raw_tax = Decimal("0")
    bonus_tax = round_apply(raw_tax, 0, RoundingPolicy.DOWN)

    base_ann = base_tax * Decimal("12")
    comb_ann = comb_tax * Decimal("12")

    trace.step("months_applied",       str(months))
    trace.step("combined_monthly",     str(combined))
    trace.step("base_monthly_tax",     str(base_tax))
    trace.step("combined_monthly_tax", str(comb_tax))
    trace.output(str(bonus_tax))

    resp: dict[str, Any] = {
        "bonus":                 str(bonus),
        "monthly_salary":        str(monthly),
        "method":                method,
        "payment_period_months": payment_period_months,
        "base_monthly_tax":      str(base_tax),
        "combined_monthly_tax":  str(comb_tax),
        "base_annual_tax":       str(base_ann),
        "combined_annual_tax":   str(comb_ann),
        "bonus_tax":             str(bonus_tax),
        "policy_version":        pv,
        "trace":                 trace.to_dict(),
    }
    return cast(KrBonusTaxResult, enrich_response(resp, wh_doc))
