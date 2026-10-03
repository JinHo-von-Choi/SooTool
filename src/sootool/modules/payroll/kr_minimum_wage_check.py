"""Korean minimum wage compliance check (최저임금 적용 검토).

Author: 최진호
Date: 2026-10-03

최저임금법 제5조·제6조, 시행령 제3조·제5조·제5조의2, 시행규칙 제2조, 연도별 최저임금 고시:

  1. 적용 최저시급 = 고시 시간급, 수습 감액 요건(1년 이상 계약, 수습 시작 3개월 이내,
     단순노무 고시 직종 아님)을 모두 갖추면 10% 감액 (법 제5조제2항, 시행령 제3조)
  2. 1개월 최저임금 적용기준 시간 = (1주 소정근로시간 + 주휴시간) × 365 / 7 / 12
     (시행령 제5조제1항제3호, 정수 시간 반올림, 주 40시간이면 209시간)
  3. 기본 임금의 시간급 환산 (시행령 제5조제1항)
  4. 상여금 등·현금 복리후생비: 월 지급액 - 월 환산액 × 산입 제외 비율 (법 제6조제4항제2호·제3호나목,
     부칙 <법률 제15666호> 제2조, 2024년부터 0%), 월 환산액 = 시간급 최저임금액 × 월 기준시간 (시행령 제5조의2)
  5. 비교 시급 = 각 환산액의 합 (시행령 제5조제3항), 적용 최저시급 이상이면 충족
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.payroll.kr_weekly_holiday_pay import (
    WAGE_UNITS,
    amount_round,
    hourly_from_wage,
    non_negative,
    plain,
    resolve_hour_basis,
)
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class MinimumWageInclusion(TypedDict):
    base_hourly:           str
    bonus_included:        str
    bonus_excluded:        str
    welfare_cash_included: str
    welfare_cash_excluded: str


class LaborPayPolicyRef(TypedDict):
    sha256:         str
    effective_date: str


class MinimumWageCheckResult(PolicyResult):
    statutory_hourly_minimum:    str
    applicable_hourly_minimum:   str
    probation_reduction_applied: bool
    notice_monthly_hours:        str
    notice_monthly_amount:       str
    weekly_basis_hours:          str
    monthly_standard_hours:      str
    monthly_conversion_amount:   str
    minimum_monthly_amount:      str
    inclusion:                   MinimumWageInclusion
    hourly_equivalent:           str
    compliant:                   bool
    hourly_shortfall:            str
    monthly_shortfall:           str
    labor_pay_policy:            LaborPayPolicyRef


def _included(amount: Decimal, base: Decimal, rate: Decimal) -> tuple[Decimal, Decimal]:
    """월 지급액 중 월 환산액 × 비율 부분을 빼고 (산입분, 제외분)을 돌려준다."""
    excluded = base * rate
    if excluded > amount:
        excluded = amount
    return amount - excluded, excluded


@REGISTRY.tool(
    namespace="payroll",
    name="kr_minimum_wage_check",
    description=(
        "한국 최저임금 충족 여부를 검토한다(최저임금법 제5조·제6조, 시행령 제5조, 연도별 고시). wage_amount 는 wage_unit 단위의 "
        "매월 정기 지급 소정근로 임금(원)이고 월급은 주 40시간이면 209시간으로 시급 환산한다. 매월 주는 상여금과 현금 복리후생비는 "
        "산입 제외 비율(2024년부터 0%)을 빼고 더하며, 수습 감액 10%는 세 요건을 모두 줄 때만 적용한다. 비교는 정밀 값이고 "
        "부족액은 원 미만 올림이다. 연장·휴일·야간 수당, 연차 미사용수당, 현물 복리후생, 1개월 초과 주기 상여는 넣지 않는다. "
        "도급제, 택시 운전, 적용 제외 인가는 다루지 않는다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_minimum_wage_check(
    wage_amount:               str,
    year:                      int,
    wage_unit:                 str        = "monthly",
    weekly_contract_hours:     str        = "40",
    daily_contract_hours:      str | None = None,
    weekly_paid_hours:         str | None = None,
    monthly_standard_hours:    str | None = None,
    monthly_bonus:             str        = "0",
    monthly_welfare_cash:      str        = "0",
    on_probation:              bool       = False,
    contract_one_year_or_more: bool       = False,
    simple_labor_job:          bool       = False,
) -> MinimumWageCheckResult:
    """Check whether a wage meets the Korean statutory minimum wage.

    Args:
        wage_amount:               매월 1회 이상 정기 지급하는 소정근로 대가 임금(원, wage_unit 단위)
        year:                      적용 연도(최저임금 고시 연도)
        wage_unit:                 hourly | daily | weekly | monthly
        weekly_contract_hours:     1주 소정근로시간(기본 40)
        daily_contract_hours:      1일 소정근로시간(wage_unit=daily 일 때 필수)
        weekly_paid_hours:         주휴로 유급 처리되는 1주 시간(생략하면 주휴 규칙으로 계산)
        monthly_standard_hours:    1개월 최저임금 적용기준 시간(생략하면 환산)
        monthly_bonus:             매월 지급하는 상여금 등(시행규칙 제2조제2항)의 월 지급액(원)
        monthly_welfare_cash:      매월 통화로 지급하는 식비·숙박비·교통비 등의 월 지급액(원)
        on_probation:              수습 시작일부터 3개월 이내인 수습 근로자 여부
        contract_one_year_or_more: 1년 이상의 기간을 정한 근로계약 여부
        simple_labor_job:          단순노무업무 고시 직종 종사 여부

    Returns:
        {statutory_hourly_minimum, applicable_hourly_minimum, probation_reduction_applied,
         notice_monthly_hours, notice_monthly_amount, weekly_basis_hours, monthly_standard_hours,
         monthly_conversion_amount, minimum_monthly_amount, inclusion, hourly_equivalent,
         compliant, hourly_shortfall, monthly_shortfall, labor_pay_policy, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_minimum_wage_check",
        formula=(
            "적용 최저시급 = 고시 시급 × (1 - 수습 감액률); "
            "월 기준시간 = (주 소정 + 주휴) × 365 / 7 / 12; "
            "비교 시급 = 기본 임금 시급 환산 + (상여 - 월 환산액 × 제외율) / 월 기준시간 "
            "+ (현금 복리후생 - 월 환산액 × 제외율) / 월 기준시간; 충족 = 비교 시급 >= 적용 최저시급"
        ),
    )

    if wage_unit not in WAGE_UNITS:
        raise InvalidInputError(f"wage_unit은 {', '.join(WAGE_UNITS)} 중 하나여야 합니다: {wage_unit!r}")
    wage    = non_negative("wage_amount", wage_amount)
    bonus   = non_negative("monthly_bonus", monthly_bonus)
    welfare = non_negative("monthly_welfare_cash", monthly_welfare_cash)

    labor_doc  = policy_load("payroll", "kr_labor_pay", year)
    policy_doc = policy_load("payroll", "kr_minimum_wage", year)
    rules      = labor_doc["data"]
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    basis = resolve_hour_basis(weekly_contract_hours, weekly_paid_hours, monthly_standard_hours, rules)

    trace.input("wage_amount",               wage_amount)
    trace.input("year",                      year)
    trace.input("wage_unit",                 wage_unit)
    trace.input("weekly_contract_hours",     weekly_contract_hours)
    trace.input("daily_contract_hours",      daily_contract_hours)
    trace.input("weekly_paid_hours",         weekly_paid_hours)
    trace.input("monthly_standard_hours",    monthly_standard_hours)
    trace.input("monthly_bonus",             monthly_bonus)
    trace.input("monthly_welfare_cash",      monthly_welfare_cash)
    trace.input("on_probation",              on_probation)
    trace.input("contract_one_year_or_more", contract_one_year_or_more)
    trace.input("simple_labor_job",          simple_labor_job)
    trace.input("policy_version",            pv)

    statutory = Decimal(str(data["hourly_minimum_wage"]))
    reduced   = on_probation and contract_one_year_or_more and not simple_labor_job
    rate_cut  = Decimal(str(data["probation"]["reduction_rate"])) if reduced else Decimal("0")
    minimum   = statutory * (Decimal("1") - rate_cut)

    conversion = statutory * basis.monthly_basis
    inclusion  = data["inclusion"]
    bonus_in, bonus_ex = _included(bonus, conversion, Decimal(str(inclusion["bonus_exclusion_rate"])))
    welf_in, welf_ex   = _included(welfare, conversion, Decimal(str(inclusion["welfare_cash_exclusion_rate"])))

    base_hourly = hourly_from_wage(wage, wage_unit, daily_contract_hours, basis)
    if wage_unit == "monthly":
        # 월 단위 금액은 합산 후 한 번만 나눠 경계값 비교에 나눗셈 오차가 끼지 않게 한다.
        equivalent = (wage + bonus_in + welf_in) / basis.monthly_basis
    else:
        equivalent = base_hourly + (bonus_in + welf_in) / basis.monthly_basis
    compliant   = equivalent >= minimum
    shortfall   = Decimal("0") if compliant else minimum - equivalent

    minimum_monthly   = amount_round(minimum * basis.monthly_basis, rules)
    monthly_shortfall = amount_round(shortfall * basis.monthly_basis, rules)

    trace.step("probation_reduction_applied", reduced)
    trace.step("applicable_hourly_minimum",   plain(minimum))
    trace.step("weekly_basis_hours",          plain(basis.weekly_basis))
    trace.step("monthly_standard_hours",      plain(basis.monthly_basis))
    trace.step("monthly_conversion_amount",   plain(conversion))
    trace.step("base_hourly",                 plain(base_hourly))
    trace.step("bonus_included",              plain(bonus_in))
    trace.step("welfare_cash_included",       plain(welf_in))
    trace.step("hourly_equivalent",           plain(equivalent))
    trace.output({"compliant": compliant, "hourly_shortfall": plain(shortfall)})

    resp: dict[str, Any] = {
        "statutory_hourly_minimum":    plain(statutory),
        "applicable_hourly_minimum":   plain(minimum),
        "probation_reduction_applied": reduced,
        "notice_monthly_hours":        str(data["notice_monthly_hours"]),
        "notice_monthly_amount":       str(data["notice_monthly_amount"]),
        "weekly_basis_hours":          plain(basis.weekly_basis),
        "monthly_standard_hours":      plain(basis.monthly_basis),
        "monthly_conversion_amount":   str(amount_round(conversion, rules)),
        "minimum_monthly_amount":      str(minimum_monthly),
        "inclusion": {
            "base_hourly":           str(round_apply(base_hourly, 2, RoundingPolicy.DOWN)),
            "bonus_included":        plain(bonus_in),
            "bonus_excluded":        plain(bonus_ex),
            "welfare_cash_included": plain(welf_in),
            "welfare_cash_excluded": plain(welf_ex),
        },
        "hourly_equivalent": str(round_apply(equivalent, 2, RoundingPolicy.DOWN)),
        "compliant":         compliant,
        "hourly_shortfall":  str(round_apply(shortfall, 2, RoundingPolicy.CEIL)),
        "monthly_shortfall": str(monthly_shortfall),
        "labor_pay_policy": {
            "sha256":         labor_doc["policy_version"]["sha256"],
            "effective_date": labor_doc["policy_version"]["effective_date"],
        },
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return cast(MinimumWageCheckResult, enrich_response(resp, policy_doc))
