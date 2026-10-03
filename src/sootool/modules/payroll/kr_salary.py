"""Korean payroll / 월급 명세서 계산기.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03

  1. 과세급여 = 월급 - min(식대, 비과세 식대 한도) (소득세법 제12조제3호러목)
  2. 국민연금 = clip(과세급여의 천원 미만 버림, 하한, 상한) x 근로자 요율 (국민연금법 시행령 제5조)
  3. 건강보험 = clip(과세급여 x 근로자 요율, 월 하한/2, 월 상한/2) (보험료 상·하한 고시, 근로자 100분의 50)
  4. 장기요양 = 건강보험 x (장기요양보험료율 / 건강보험료율) (노인장기요양보험법 제9조제1항)
  5. 고용보험 = 과세급여 x 근로자 요율, 산재보험 근로자 부담 없음
  6. 소득세 = 근로소득 간이세액표(소득세법 시행령 별표 2) 조회, 8세 이상 20세 이하 자녀 차감
  7. 지방소득세 = 소득세 x 10% (지방세법 제103조의13제1항)
  건강보험료와 장기요양보험료는 10원 미만(원 단위)을 버리고 나머지 보험료와 지방소득세는 원 미만을 버린다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax.kr_withholding import lookup_simple_tax
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class SalaryInsurances(TypedDict):
    """근로자 부담 4대보험료(원 문자열)."""

    national_pension:     str
    health_insurance:     str
    long_term_care:       str
    employment_insurance: str
    industrial_accident:  str
    total:                str


class SalaryTaxes(TypedDict):
    """월 원천징수 소득세와 지방소득세(원 문자열)."""

    income_tax:       str
    local_income_tax: str
    total:            str


class IncomeTaxLookup(TypedDict):
    """간이세액표 조회 내역. ``row`` 는 조회한 행 또는 산식 구간이며 method 에 따라 모양이 다르다."""

    method:                str
    salary_k:              str
    row:                   dict[str, Any] | None
    table_tax:             str
    child_reduction:       str
    policy_effective_date: str


class KrSalaryResult(PolicyResult):
    gross:             str
    non_taxable:       str
    taxable:           str
    insurances:        SalaryInsurances
    taxes:             SalaryTaxes
    income_tax_lookup: IncomeTaxLookup
    net:               str


def _round_krw(value: Decimal) -> Decimal:
    """원 미만 버림."""
    return round_apply(value, 0, RoundingPolicy.DOWN)


def _clip(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _truncate_premium(value: Decimal, unit: Decimal) -> Decimal:
    """보험료를 unit 원 단위로 절사한다. 비율의 자릿수 한계로 생기는 미소 오차는 먼저 정리한다."""
    return _truncate_to_unit(round_apply(value, 6, RoundingPolicy.HALF_UP), unit)


def _truncate_to_unit(value: Decimal, unit: Decimal) -> Decimal:
    """unit 원 미만을 버린다 (unit=1000 이면 천원 미만 버림)."""
    return round_apply(value / unit, 0, RoundingPolicy.DOWN) * unit


@REGISTRY.tool(
    namespace="payroll",
    name="kr_salary",
    description=(
        "세전 월급(원, 문자열)에서 한국 실수령액을 구한다. 비과세 식대 한도를 뺀 과세급여로 4대보험 근로자 부담분"
        "(국민연금 상·하한, 건강보험, 장기요양, 고용보험)과 근로소득 간이세액표 소득세, 지방소득세(소득세의 10%)를 "
        "공제하며 건강보험과 장기요양은 10원 미만 버림, 그 밖의 보험료와 지방소득세는 원 미만 버림이다. 시행일별 정책을 as_of 로 고른다. 연봉을 월급 자리에 넣으면 안 된다."
    ),
    version="2.0.0",
    policy=True,
)
def payroll_kr_salary(
    monthly_salary:     str,
    year:               int,
    meal_allowance:     str = "0",
    num_dependents:     int = 1,
    children_8_20:      int = 0,
) -> KrSalaryResult:
    """Calculate monthly net pay from gross monthly salary.

    Args:
        monthly_salary: 월급여(세전, 원). 식대 포함한 총지급액
        year:           과세연도
        meal_allowance: 월 식대(원). 비과세 한도까지만 공제
        num_dependents: 간이세액표 공제대상가족 수(본인 포함, 1 이상)
        children_8_20:  공제대상가족 중 8세 이상 20세 이하 자녀 수(기본 0)

    Returns:
        {gross, non_taxable, taxable, insurances, taxes, income_tax_lookup, net, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_salary",
        formula=(
            "과세급여 = 월급 - min(식대, 식대한도); "
            "국민연금 = clip(천원 미만 버린 과세급여, 하한, 상한) * 근로자 요율; "
            "건강보험 = clip(과세급여 * 근로자 요율, 월 하한/2, 월 상한/2); "
            "장기요양 = 건강보험 * (장기요양보험료율/건강보험료율); "
            "고용보험 = 과세급여 * 근로자 요율; "
            "소득세 = 근로소득 간이세액표(과세급여, 공제대상가족, 8~20세 자녀); "
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
    if children_8_20 < 0:
        raise InvalidInputError("children_8_20은 0 이상이어야 합니다.")
    if children_8_20 > num_dependents - 1:
        raise InvalidInputError("children_8_20은 본인을 제외한 공제대상가족 수(num_dependents - 1)를 넘을 수 없습니다.")
    if meal > gross:
        raise InvalidInputError("meal_allowance는 monthly_salary를 초과할 수 없습니다.")

    policy_doc = policy_load("payroll", "kr_4insurance", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("monthly_salary", monthly_salary)
    trace.input("year",           year)
    trace.input("meal_allowance", meal_allowance)
    trace.input("num_dependents", num_dependents)
    trace.input("children_8_20",  children_8_20)

    # --- 비과세 식대 한도 차감 ---
    meal_cap     = D(str(data["non_taxable"]["meal_monthly_cap"]))
    non_taxable  = meal if meal <= meal_cap else meal_cap
    taxable      = gross - non_taxable

    # --- 국민연금: 소득월액 끝수 버림 후 하한/상한 적용 ---
    np_cfg    = data["national_pension"]
    np_unit   = D(str(np_cfg.get("base_truncation_unit", 1)))
    np_base   = _clip(
        _truncate_to_unit(taxable, np_unit),
        D(str(np_cfg["base_min_monthly"])),
        D(str(np_cfg["base_max_monthly"])),
    )
    np_rate   = D(str(np_cfg["employee_rate"]))
    national_pension = _round_krw(np_base * np_rate)

    # --- 건강보험(월별 보험료액 하한/상한의 근로자 부담분) + 장기요양 ---
    hi_cfg    = data["health_insurance"]
    hi_rate   = D(str(hi_cfg["employee_rate"]))
    hi_share  = hi_rate / (hi_rate + D(str(hi_cfg["employer_rate"])))
    hi_unit           = D(str(hi_cfg.get("premium_truncation_unit", 1)))
    health_insurance  = _truncate_premium(taxable * hi_rate, hi_unit)
    if hi_cfg.get("premium_min_monthly_total") is not None:
        hi_floor = _truncate_premium(D(str(hi_cfg["premium_min_monthly_total"])) * hi_share, hi_unit)
        health_insurance = max(health_insurance, hi_floor)
    if hi_cfg.get("premium_max_monthly_total") is not None:
        hi_ceiling = _truncate_premium(D(str(hi_cfg["premium_max_monthly_total"])) * hi_share, hi_unit)
        health_insurance = min(health_insurance, hi_ceiling)
    ltc_rate  = D(str(hi_cfg["long_term_care_rate_of_health"]))
    long_term_care    = _truncate_premium(health_insurance * ltc_rate, hi_unit)

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

    # --- 소득세: 근로소득 간이세액표 조회 (월급여액 = 비과세 제외 과세급여) ---
    wh_doc     = policy_load("tax", "kr_withholding", year)
    lookup     = lookup_simple_tax(taxable, num_dependents, children_8_20, wh_doc["data"])
    income_tax = lookup.tax

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

    income_tax_lookup = {
        "method":                 lookup.method,
        "salary_k":               str(lookup.salary_k),
        "row":                    lookup.row,
        "table_tax":              str(lookup.table_tax),
        "child_reduction":        str(lookup.child_reduction),
        "policy_effective_date":  wh_doc["policy_version"]["effective_date"],
    }

    trace.step("non_taxable",        str(non_taxable))
    trace.step("taxable",            str(taxable))
    trace.step("national_pension_base", str(np_base))
    trace.step("insurances",         insurances)
    trace.step("income_tax_lookup",  income_tax_lookup)
    trace.step("taxes",              taxes)
    trace.output(str(net))

    resp: dict[str, Any] = {
        "gross":             str(gross),
        "non_taxable":       str(non_taxable),
        "taxable":           str(taxable),
        "insurances":        insurances,
        "taxes":             taxes,
        "income_tax_lookup": income_tax_lookup,
        "net":               str(net),
        "policy_version":    pv,
        "trace":             trace.to_dict(),
    }
    return cast(KrSalaryResult, enrich_response(resp, policy_doc))
