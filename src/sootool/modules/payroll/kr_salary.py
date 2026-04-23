"""Korean payroll / 월급 명세서 계산기.

Author: 최진호
Date: 2026-04-23

4대보험 (국민연금·건강보험·장기요양·고용보험·산재) 근로자 부담액 공제,
비과세 식대 한도 차감, 소득세 간이 추정 (연환산 누진), 지방소득세 10%.
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


def _round_krw(value: Decimal) -> Decimal:
    """10원 단위 버림 (KRW convention)."""
    return round_apply(value, 0, RoundingPolicy.DOWN)


def _clip(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


@REGISTRY.tool(
    namespace="payroll",
    name="kr_salary",
    description=(
        "한국 월급 → 실수령액 계산. 4대보험(국민연금·건강보험·장기요양·고용보험) "
        "근로자 부담, 비과세 식대, 소득세/지방소득세 공제."
    ),
    version="1.0.0",
)
def payroll_kr_salary(
    monthly_salary:     str,
    year:               int,
    meal_allowance:     str = "0",
    num_dependents:     int = 1,
) -> dict[str, Any]:
    """Calculate monthly net pay from gross monthly salary.

    Args:
        monthly_salary: 월급여(세전, 원). 식대 포함한 총지급액
        year:           과세연도
        meal_allowance: 월 식대(원). 비과세 한도까지만 공제
        num_dependents: 부양가족 수(본인 포함, 간이세액 근사에 사용 — 현 버전은 참고용)

    Returns:
        {gross, taxable, insurances, taxes, net, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_salary",
        formula=(
            "과세소득 = 월급 - min(식대, 식대한도); "
            "국민연금 = clip(과세소득, 하한, 상한) * 4.5%; "
            "건강보험 = 과세소득 * 3.595%; "
            "장기요양 = 건강보험 * 12.95%; "
            "고용보험 = 과세소득 * 0.9%; "
            "소득세 = kr_income(과세소득*12) / 12 [간이 추정]; "
            "지방소득세 = 소득세 * 10%; "
            "net = 월급 - (국민연금+건강보험+장기요양+고용보험+소득세+지방소득세)"
        ),
    )

    gross = D(monthly_salary)
    meal  = D(meal_allowance)

    if gross <= Decimal("0"):
        raise InvalidInputError("monthly_salary는 0보다 커야 합니다.")
    if meal < Decimal("0"):
        raise InvalidInputError("meal_allowance는 0 이상이어야 합니다.")
    if num_dependents < 1:
        raise InvalidInputError("num_dependents는 1 이상이어야 합니다.")
    if meal > gross:
        raise InvalidInputError("meal_allowance는 monthly_salary를 초과할 수 없습니다.")

    policy_doc = policy_load("payroll", "kr_4insurance", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("monthly_salary", monthly_salary)
    trace.input("year",           year)
    trace.input("meal_allowance", meal_allowance)
    trace.input("num_dependents", num_dependents)

    # --- 비과세 식대 한도 차감 ---
    meal_cap     = D(str(data["non_taxable"]["meal_monthly_cap"]))
    non_taxable  = meal if meal <= meal_cap else meal_cap
    taxable      = gross - non_taxable

    # --- 국민연금 (하한/상한 적용) ---
    np_cfg    = data["national_pension"]
    np_base   = _clip(
        taxable,
        D(str(np_cfg["base_min_monthly"])),
        D(str(np_cfg["base_max_monthly"])),
    )
    np_rate   = D(str(np_cfg["employee_rate"]))
    national_pension = _round_krw(np_base * np_rate)

    # --- 건강보험 + 장기요양 ---
    hi_cfg    = data["health_insurance"]
    hi_rate   = D(str(hi_cfg["employee_rate"]))
    health_insurance  = _round_krw(taxable * hi_rate)
    ltc_rate  = D(str(hi_cfg["long_term_care_rate_of_health"]))
    long_term_care    = _round_krw(health_insurance * ltc_rate)

    # --- 고용보험 ---
    ei_rate   = D(str(data["employment_insurance"]["employee_rate"]))
    employment_insurance = _round_krw(taxable * ei_rate)

    # --- 산재: 근로자 부담 0 (정책 명시) ---
    ia_rate   = D(str(data["industrial_accident"]["employee_rate"]))
    industrial_accident = _round_krw(taxable * ia_rate)

    insurance_total = (
        national_pension + health_insurance + long_term_care
        + employment_insurance + industrial_accident
    )

    # --- 소득세 간이 추정: 연환산 후 kr_income 누진 적용, 월할 ---
    # 간이세액표 정확 재현은 별도 정책이 필요. 본 도구는 연환산 누진 근사.
    annual_taxable   = taxable * Decimal("12") - insurance_total * Decimal("12")
    if annual_taxable < Decimal("0"):
        annual_taxable = Decimal("0")

    income_policy_doc = policy_load("tax", "kr_income", year)
    income_brackets   = income_policy_doc["data"]["brackets"]
    annual_tax, _, _, _ = _calc_progressive(
        annual_taxable, income_brackets, RoundingPolicy.HALF_UP, 0
    )
    income_tax = _round_krw(annual_tax / Decimal("12"))

    local_rate = D(str(data["local_income_tax"]["rate_of_income_tax"]))
    local_tax  = _round_krw(income_tax * local_rate)

    tax_total = income_tax + local_tax

    net = gross - insurance_total - tax_total

    insurances = {
        "national_pension":      str(national_pension),
        "health_insurance":      str(health_insurance),
        "long_term_care":        str(long_term_care),
        "employment_insurance":  str(employment_insurance),
        "industrial_accident":   str(industrial_accident),
        "total":                 str(insurance_total),
    }
    taxes = {
        "income_tax":        str(income_tax),
        "local_income_tax":  str(local_tax),
        "total":             str(tax_total),
    }

    trace.step("non_taxable", str(non_taxable))
    trace.step("taxable",     str(taxable))
    trace.step("insurances",  insurances)
    trace.step("taxes",       taxes)
    trace.output(str(net))

    resp: dict[str, Any] = {
        "gross":          str(gross),
        "non_taxable":    str(non_taxable),
        "taxable":        str(taxable),
        "insurances":     insurances,
        "taxes":          taxes,
        "net":            str(net),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
