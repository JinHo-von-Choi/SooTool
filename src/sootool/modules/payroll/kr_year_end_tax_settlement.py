"""Korean year-end tax settlement (연말정산) calculator.

Author: 최진호
Date: 2026-04-24

연말정산 환급/추가납부 간이 모델 (소득세법 제47조·제50조·제55조):

  1. 근로소득공제 계산 (kr_withholding 정책 재사용)
  2. 기본공제 = 본인 + 부양가족 * 150만원
  3. 표준세액공제 또는 산정세액공제 중 선택 (본 모델은 표준세액공제 13만원)
  4. 과세표준 = 연간급여 - 근로소득공제 - 기본공제
  5. 산출세액 = progressive(과세표준)
  6. 결정세액 = max(0, 산출세액 - 세액공제)
  7. 환급액 = 기납부세액 - 결정세액 (양수: 환급, 음수: 추가납부)
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

STANDARD_TAX_CREDIT = Decimal("130000")


@REGISTRY.tool(
    namespace="payroll",
    name="kr_year_end_tax_settlement",
    description=(
        "한국 연말정산 환급/추가납부 계산. 근로소득공제·기본공제·"
        "표준세액공제 기반 간이 모델."
    ),
    version="1.0.0",
)
def payroll_kr_year_end_tax_settlement(
    annual_gross:       str,
    prepaid_tax:        str,
    year:               int,
    dependents:         int = 1,
    extra_deductions:   str = "0",
    extra_tax_credits:  str = "0",
) -> dict[str, Any]:
    """Calculate year-end tax settlement refund or additional tax due.

    Args:
        annual_gross:       연간 총급여(원)
        prepaid_tax:        당해 연도 기납부세액(원천징수 합계, 원)
        year:               귀속연도
        dependents:         부양가족 수(본인 포함, 최소 1)
        extra_deductions:   추가 소득공제(연금보험료·특별소득공제 등, 원)
        extra_tax_credits:  추가 세액공제(자녀·의료비·교육비 등, 원)

    Returns:
        {annual_gross, labor_deduction, personal_deduction, taxable_income,
         computed_tax, tax_credit, decided_tax, prepaid_tax, refund, status,
         policy_version, trace}
        status: "refund" | "additional" | "settled"
    """
    trace = CalcTrace(
        tool="payroll.kr_year_end_tax_settlement",
        formula=(
            "과세표준 = 연간급여 - 근로소득공제 - 기본공제 - 추가공제; "
            "산출세액 = progressive(과세표준); "
            "결정세액 = max(0, 산출세액 - 표준세액공제 - 추가세액공제); "
            "환급액 = 기납부세액 - 결정세액"
        ),
    )

    gross           = D(annual_gross)
    prepaid         = D(prepaid_tax)
    extra_ded       = D(extra_deductions)
    extra_credit    = D(extra_tax_credits)

    if gross < Decimal("0"):
        raise InvalidInputError("annual_gross는 0 이상이어야 합니다.")
    if prepaid < Decimal("0"):
        raise InvalidInputError("prepaid_tax는 0 이상이어야 합니다.")
    if dependents < 1:
        raise InvalidInputError("dependents는 1 이상이어야 합니다 (본인 포함).")
    if extra_ded < Decimal("0"):
        raise InvalidInputError("extra_deductions는 0 이상이어야 합니다.")
    if extra_credit < Decimal("0"):
        raise InvalidInputError("extra_tax_credits는 0 이상이어야 합니다.")

    # 간이세액표 정책에서 근로소득공제 브래킷/기본공제 재사용
    wh_doc      = policy_load("tax", "kr_withholding", year)
    wh_data     = wh_doc["data"]
    labor_brkts = wh_data["labor_income_deduction_brackets"]
    personal_ded_unit = D(str(wh_data["personal_deduction"]))

    # 세율 구간은 kr_income 정책 사용 (설계: 단일 소스)
    inc_doc     = policy_load("tax", "kr_income", year)
    brackets    = inc_doc["data"]["brackets"]
    pv          = inc_doc["policy_version"]

    trace.input("annual_gross",      annual_gross)
    trace.input("prepaid_tax",       prepaid_tax)
    trace.input("year",              year)
    trace.input("dependents",        dependents)
    trace.input("extra_deductions",  extra_deductions)
    trace.input("extra_tax_credits", extra_tax_credits)
    trace.input("policy_version",    pv)

    labor_ded      = _calc_labor_income_deduction(gross, labor_brkts)
    personal_total = personal_ded_unit * Decimal(str(dependents))

    taxable = gross - labor_ded - personal_total - extra_ded
    if taxable < Decimal("0"):
        taxable = Decimal("0")

    computed_tax, _eff, _marg, breakdown = _calc_progressive(
        taxable, brackets, RoundingPolicy.HALF_UP, 0
    )

    tax_credit = STANDARD_TAX_CREDIT + extra_credit
    decided    = computed_tax - tax_credit
    if decided < Decimal("0"):
        decided = Decimal("0")
    decided = round_apply(decided, 0, RoundingPolicy.DOWN)

    refund = prepaid - decided
    if refund > Decimal("0"):
        status = "refund"
    elif refund < Decimal("0"):
        status = "additional"
    else:
        status = "settled"

    trace.step("labor_deduction",     str(labor_ded))
    trace.step("personal_deduction",  str(personal_total))
    trace.step("taxable_income",      str(taxable))
    trace.step("computed_tax",        str(computed_tax))
    trace.step("tax_credit",          str(tax_credit))
    trace.step("decided_tax",         str(decided))
    trace.step("breakdown",           breakdown)
    trace.output(str(refund))

    resp: dict[str, Any] = {
        "annual_gross":       str(gross),
        "labor_deduction":    str(labor_ded),
        "personal_deduction": str(personal_total),
        "taxable_income":     str(taxable),
        "computed_tax":       str(computed_tax),
        "tax_credit":         str(tax_credit),
        "decided_tax":        str(decided),
        "prepaid_tax":        str(prepaid),
        "refund":             str(refund),
        "status":             status,
        "policy_version":     pv,
        "trace":              trace.to_dict(),
    }
    return enrich_response(resp, inc_doc)
