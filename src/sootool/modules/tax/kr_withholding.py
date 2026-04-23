"""Korean withholding tax (간이 원천징수세액) calculator.

Author: 최진호
Date: 2026-04-22

근로소득 간이세액표 근사 공식:
  1. 연간 급여 = 월급여 * 12
  2. 근로소득공제 계산 (노동소득공제 구간표 적용)
  3. 소득공제 = 근로소득공제 + 기본공제(본인 + 부양가족 * 인당 150만)
  4. 과세표준 = 연간급여 - 소득공제
  5. 산출세액 = 과세표준에 소득세율 적용
  6. 세액공제 = 부양가족 수 * 월 15,830원 * 12
  7. 결정세액 = max(0, 산출세액 - 세액공제)
  8. 월 원천징수 = 결정세액 / 12
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
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


def _calc_labor_income_deduction(
    annual_income: Decimal,
    brackets:      list[dict[str, Any]],
) -> Decimal:
    """근로소득공제 계산 (누진 공제 구간)."""
    lower     = Decimal("0")
    deduction = Decimal("0")

    for bracket in brackets:
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))
        offset    = D(str(bracket["offset"]))

        upper = None if upper_raw is None else D(str(upper_raw))

        if upper is not None and annual_income <= lower:
            lower = upper
            continue

        if upper is None:
            taxable_in = annual_income - lower if annual_income > lower else Decimal("0")
        else:
            cap        = min(annual_income, upper)
            taxable_in = cap - lower if cap > lower else Decimal("0")

        if taxable_in > Decimal("0"):
            deduction = offset + taxable_in * rate
            # offset represents cumulative deduction at the bottom of this bracket
            # recalculate properly: deduction at top of lower brackets + this bracket
            pass

        if upper is not None:
            lower = upper
            if annual_income <= upper:
                break

    # Re-compute correctly: iterate once and accumulate
    lower     = Decimal("0")
    deduction = Decimal("0")
    for bracket in brackets:
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))
        upper     = None if upper_raw is None else D(str(upper_raw))

        if annual_income <= lower:
            break

        cap        = annual_income if upper is None else min(annual_income, upper)
        taxable_in = cap - lower
        if taxable_in > Decimal("0"):
            deduction += taxable_in * rate

        if upper is not None:
            lower = upper
        else:
            break

    return deduction


@REGISTRY.tool(
    namespace="tax",
    name="kr_withholding_simple",
    description=(
        "근로소득 간이 원천징수세액 계산 (간이세액표 근사 공식)."
    ),
    version="1.0.0",
)
def tax_kr_withholding_simple(
    monthly_salary: str,
    dependents:     int,
    year:           int,
) -> dict[str, Any]:
    """Calculate simplified monthly withholding tax for Korean employees.

    Uses an approximation formula based on the 간이세액표 structure.
    Real 간이세액표 is a lookup table; this uses the underlying formula.

    Args:
        monthly_salary: 월 급여 (Decimal string, 원)
        dependents:     부양가족 수 (본인 포함, 최소 1)
        year:           과세연도

    Returns:
        {withheld_tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_withholding_simple",
        formula=(
            "연간급여 → 근로소득공제 → 과세표준 → 산출세액 → "
            "부양가족공제 → 결정세액 / 12"
        ),
    )

    monthly = D(monthly_salary)

    if monthly < Decimal("0"):
        raise InvalidInputError("monthly_salary는 0 이상이어야 합니다.")
    if dependents < 1:
        raise InvalidInputError("dependents는 1 이상이어야 합니다 (본인 포함).")

    policy_doc = policy_load("tax", "kr_withholding", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    labor_brackets      = data["labor_income_deduction_brackets"]
    personal_deduction  = D(str(data["personal_deduction"]))
    dep_credit_monthly  = D(str(data["dependent_credit_monthly"]))
    brackets            = data["brackets"]

    trace.input("monthly_salary", monthly_salary)
    trace.input("dependents",     dependents)
    trace.input("year",           year)

    annual_income     = monthly * 12
    labor_deduction   = _calc_labor_income_deduction(annual_income, labor_brackets)
    # 기본공제: 본인 1명 포함
    personal_total    = personal_deduction * Decimal(str(dependents))
    taxable_income    = annual_income - labor_deduction - personal_total

    if taxable_income < Decimal("0"):
        taxable_income = Decimal("0")

    annual_tax, _, _, _ = _calc_progressive(
        taxable_income, brackets, RoundingPolicy.HALF_UP, 0
    )

    dep_credit_annual = dep_credit_monthly * 12 * Decimal(str(dependents))
    decided_tax       = annual_tax - dep_credit_annual
    if decided_tax < Decimal("0"):
        decided_tax = Decimal("0")

    monthly_withheld = round_apply(decided_tax / 12, 0, RoundingPolicy.DOWN)

    trace.step("annual_income",    str(annual_income))
    trace.step("labor_deduction",  str(labor_deduction))
    trace.step("personal_total",   str(personal_total))
    trace.step("taxable_income",   str(taxable_income))
    trace.step("annual_tax",       str(annual_tax))
    trace.step("dep_credit_annual",str(dep_credit_annual))
    trace.step("decided_tax",      str(decided_tax))
    trace.output(str(monthly_withheld))

    resp = {
        "withheld_tax":   str(monthly_withheld),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
