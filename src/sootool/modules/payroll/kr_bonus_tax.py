"""Korean bonus withholding tax (상여 세액) calculator.

Author: 최진호
Date: 2026-04-24

상여 세액 계산 두 방식:

  method="simple" (간이세액표 근사):
    - 상여를 월급여에 합산 → 간이세액표 근사 세액 - 정규 월 세액
  method="averaging" (연분연승법, 소득세법 제129조):
    - 지급대상기간(월수)으로 상여 평균 → 월급여 합산 → 연환산 세액
    - (합산기준 연세액 - 정규 연세액) * 월수 / 12 = 상여에 대한 추가 원천징수세
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
from sootool.modules.tax.kr_withholding import _calc_labor_income_deduction
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_VALID_METHODS = {"simple", "averaging"}


def _annual_tax(
    annual_income:     Decimal,
    dependents:        Decimal,
    labor_brackets:    list[dict[str, Any]],
    tax_brackets:      list[dict[str, Any]],
    personal_unit:     Decimal,
    dep_credit_month:  Decimal,
) -> Decimal:
    """연환산 원천징수 기준 연세액 산정 (근로소득공제 + 기본공제 + 부양가족세액공제)."""
    labor_ded = _calc_labor_income_deduction(annual_income, labor_brackets)
    personal  = personal_unit * dependents
    taxable   = annual_income - labor_ded - personal
    if taxable < Decimal("0"):
        taxable = Decimal("0")
    annual, _eff, _marg, _br = _calc_progressive(
        taxable, tax_brackets, RoundingPolicy.HALF_UP, 0
    )
    dep_credit = dep_credit_month * Decimal("12") * dependents
    decided = annual - dep_credit
    if decided < Decimal("0"):
        decided = Decimal("0")
    return decided


@REGISTRY.tool(
    namespace="payroll",
    name="kr_bonus_tax",
    description=(
        "한국 상여 원천징수세액 계산. simple(간이세액표 근사) 또는 "
        "averaging(연분연승법) 선택."
    ),
    version="1.0.0",
)
def payroll_kr_bonus_tax(
    bonus_amount:          str,
    monthly_salary:        str,
    year:                  int,
    dependents:            int = 1,
    method:                str = "averaging",
    payment_period_months: int = 12,
) -> dict[str, Any]:
    """Calculate withholding tax on a Korean bonus payment.

    Args:
        bonus_amount:          상여금(원, 세전)
        monthly_salary:        기본 월급여(원)
        year:                  귀속연도
        dependents:            부양가족 수 (본인 포함)
        method:                "simple" | "averaging"
        payment_period_months: 지급대상기간(연분연승법용, 1~12)

    Returns:
        {bonus, monthly_salary, method, payment_period_months,
         base_annual_tax, combined_annual_tax, bonus_tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_bonus_tax",
        formula=(
            "simple: (월급여+상여) 간이세액 - 월급여 간이세액; "
            "averaging: ((월급여+상여/월수)*12 세액 - 월급여*12 세액) * 월수 / 12"
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

    wh_doc        = policy_load("tax", "kr_withholding", year)
    wh_data       = wh_doc["data"]
    labor_brkts   = wh_data["labor_income_deduction_brackets"]
    personal_unit = D(str(wh_data["personal_deduction"]))
    dep_credit    = D(str(wh_data["dependent_credit_monthly"]))
    tax_brackets  = wh_data["brackets"]
    pv            = wh_doc["policy_version"]

    trace.input("bonus_amount",          bonus_amount)
    trace.input("monthly_salary",        monthly_salary)
    trace.input("year",                  year)
    trace.input("dependents",            dependents)
    trace.input("method",                method)
    trace.input("payment_period_months", payment_period_months)
    trace.input("policy_version",        pv)

    deps_d = Decimal(str(dependents))

    if method == "averaging":
        months     = Decimal(str(payment_period_months))
        # 지급대상기간 평균 월상여
        avg_bonus  = bonus / months
        combined   = monthly + avg_bonus
        base_ann   = _annual_tax(
            monthly * Decimal("12"), deps_d, labor_brkts, tax_brackets,
            personal_unit, dep_credit,
        )
        comb_ann   = _annual_tax(
            combined * Decimal("12"), deps_d, labor_brkts, tax_brackets,
            personal_unit, dep_credit,
        )
        raw_tax = (comb_ann - base_ann) * months / Decimal("12")
    else:  # simple
        # 월급여+상여 합산액을 월 단위 취급 → 연환산 세액 / 12
        combined  = monthly + bonus
        base_ann  = _annual_tax(
            monthly * Decimal("12"), deps_d, labor_brkts, tax_brackets,
            personal_unit, dep_credit,
        )
        comb_ann  = _annual_tax(
            combined * Decimal("12"), deps_d, labor_brkts, tax_brackets,
            personal_unit, dep_credit,
        )
        raw_tax = (comb_ann - base_ann) / Decimal("12")

    if raw_tax < Decimal("0"):
        raw_tax = Decimal("0")
    bonus_tax = round_apply(raw_tax, 0, RoundingPolicy.DOWN)

    trace.step("base_annual_tax",     str(base_ann))
    trace.step("combined_annual_tax", str(comb_ann))
    trace.output(str(bonus_tax))

    resp: dict[str, Any] = {
        "bonus":                 str(bonus),
        "monthly_salary":        str(monthly),
        "method":                method,
        "payment_period_months": payment_period_months,
        "base_annual_tax":       str(base_ann),
        "combined_annual_tax":   str(comb_ann),
        "bonus_tax":             str(bonus_tax),
        "policy_version":        pv,
        "trace":                 trace.to_dict(),
    }
    return enrich_response(resp, wh_doc)
