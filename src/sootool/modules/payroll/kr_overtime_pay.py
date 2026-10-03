"""Korean overtime, night and holiday work pay (연장·야간·휴일근로수당) calculator.

Author: 최진호
Date: 2026-10-03

근로기준법 제56조 가산임금:

  1. 시간급 통상임금 (시행령 제6조제2항)
       시급 그대로, 일급 / 1일 소정근로시간, 주급 / 1주 기준시간, 월급 / 월 기준시간
       1주 기준시간 = 1주 소정근로시간 + 유급 처리 시간(주휴 등)
       월 기준시간  = 1주 기준시간 × 365 / 7 / 12 (정수 시간 반올림, 주 40시간이면 209시간)
  2. 근로 자체에 대한 임금 = (연장근로시간 + 휴일근로시간) × 통상시급
  3. 가산임금
       연장근로                 × 50% (제56조제1항)
       휴일근로 하루 8시간 이내 × 50%, 8시간 초과분 × 100% (제56조제2항)
       야간근로(22시~06시)       × 50% (제56조제3항), 연장·휴일과 겹치면 각각 더한다
  4. 상시 4명 이하 사업장은 제56조를 적용하지 않으므로 가산임금은 0 (법 제11조제2항, 시행령 별표 1)
  5. 각 금액은 원 미만 올림 후 합산
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
    positive,
    resolve_hour_basis,
)
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class OvertimeHours(TypedDict):
    overtime:             str
    night:                str
    holiday_within_limit: str
    holiday_over_limit:   str


class OvertimeAmounts(TypedDict):
    overtime:             str
    night:                str
    holiday_within_limit: str
    holiday_over_limit:   str


class OvertimePayResult(PolicyResult):
    hourly_ordinary_wage:   str
    wage_unit:              str
    weekly_basis_hours:     str
    monthly_standard_hours: str
    premium_applies:        bool
    hours:                  OvertimeHours
    base_pay:               str
    premiums:               OvertimeAmounts
    premium_total:          str
    total_pay:              str


def _split_holiday(days: list[str] | None, limit: Decimal) -> tuple[Decimal, Decimal]:
    """휴일 하루별 근로시간을 8시간 이내분과 초과분으로 나눠 합산한다."""
    within = Decimal("0")
    over   = Decimal("0")
    if days is None:
        return within, over
    if not isinstance(days, list):
        raise InvalidInputError("holiday_hours_by_day는 휴일 하루별 근로시간 문자열의 목록이어야 합니다.")
    for index, value in enumerate(days):
        hours = non_negative(f"holiday_hours_by_day[{index}]", value)
        if hours > Decimal("24"):
            raise InvalidInputError(f"holiday_hours_by_day[{index}]는 24 이하여야 합니다.")
        within += hours if hours < limit else limit
        over   += hours - limit if hours > limit else Decimal("0")
    return within, over


@REGISTRY.tool(
    namespace="payroll",
    name="kr_overtime_pay",
    description=(
        "한국 연장·야간·휴일근로수당을 계산한다(근로기준법 제56조, 시행령 제6조). ordinary_wage 는 통상임금(원)이고 "
        "wage_unit 으로 시급·일급·주급·월급을 고른다(월급은 주 40시간이면 209시간으로 환산). 시간은 Decimal 문자열이며 "
        "휴일근로는 하루별 목록으로 받아 8시간 이내 50%, 초과 100%를, 연장 50%와 야간(22~06시) 50%는 겹치면 더한다. "
        "employee_count 4명 이하는 가산 없이 근로시간분만 주고 금액은 원 미만 올림이다. "
        "휴일근로 시간을 overtime_hours 에도 넣으면 이중 가산이다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_overtime_pay(
    ordinary_wage:          str,
    year:                   int,
    employee_count:         int,
    wage_unit:              str             = "hourly",
    overtime_hours:         str             = "0",
    night_hours:            str             = "0",
    holiday_hours_by_day:   list[str] | None = None,
    weekly_contract_hours:  str             = "40",
    daily_contract_hours:   str | None      = None,
    weekly_paid_hours:      str | None      = None,
    monthly_standard_hours: str | None      = None,
) -> OvertimePayResult:
    """Calculate Korean overtime, night and holiday work pay.

    Args:
        ordinary_wage:          통상임금(원). wage_unit 단위 금액
        year:                   적용 연도
        employee_count:         상시 근로자 수(근로기준법 시행령 제7조의2로 산정)
        wage_unit:              hourly | daily | weekly | monthly
        overtime_hours:         휴일근로를 뺀 연장근로시간(단시간근로자의 소정근로시간 초과분 포함)
        night_hours:            22시~06시 근로시간 전체(연장·휴일과 겹치는 시간 포함)
        holiday_hours_by_day:   휴일 하루별 근로시간 목록
        weekly_contract_hours:  1주 소정근로시간(기본 40)
        daily_contract_hours:   1일 소정근로시간(wage_unit=daily 일 때 필수)
        weekly_paid_hours:      1주 소정근로시간 외 유급 처리 시간(생략하면 주휴시간)
        monthly_standard_hours: 월 통상임금 산정 기준시간(생략하면 환산)

    Returns:
        {hourly_ordinary_wage, wage_unit, weekly_basis_hours, monthly_standard_hours,
         premium_applies, hours, base_pay, premiums, premium_total, total_pay,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_overtime_pay",
        formula=(
            "통상시급 = 통상임금 / 단위 기준시간; "
            "기본분 = (연장 + 휴일) × 통상시급; "
            "가산분 = 연장 × 0.5 + 휴일(8h 이내) × 0.5 + 휴일(8h 초과) × 1.0 + 야간 × 0.5 "
            "(상시 4명 이하면 0); 각 금액 원 미만 올림"
        ),
    )

    if wage_unit not in WAGE_UNITS:
        raise InvalidInputError(f"wage_unit은 {', '.join(WAGE_UNITS)} 중 하나여야 합니다: {wage_unit!r}")
    if isinstance(employee_count, bool) or not isinstance(employee_count, int) or employee_count < 1:
        raise InvalidInputError("employee_count는 1 이상의 정수여야 합니다.")
    wage     = positive("ordinary_wage", ordinary_wage)
    overtime = non_negative("overtime_hours", overtime_hours)
    night    = non_negative("night_hours", night_hours)

    policy_doc = policy_load("payroll", "kr_labor_pay", year)
    rules      = policy_doc["data"]
    pv         = policy_doc["policy_version"]
    rates      = rules["premium_rates"]

    limit                  = Decimal(str(rules["holiday_daily_limit_hours"]))
    holiday_in, holiday_ov = _split_holiday(holiday_hours_by_day, limit)
    basis                  = resolve_hour_basis(
        weekly_contract_hours, weekly_paid_hours, monthly_standard_hours, rules,
    )
    hourly                 = hourly_from_wage(wage, wage_unit, daily_contract_hours, basis)
    premium_applies        = employee_count > int(rules["small_workplace_max_employees"])

    trace.input("ordinary_wage",          ordinary_wage)
    trace.input("year",                   year)
    trace.input("employee_count",         employee_count)
    trace.input("wage_unit",              wage_unit)
    trace.input("overtime_hours",         overtime_hours)
    trace.input("night_hours",            night_hours)
    trace.input("holiday_hours_by_day",   holiday_hours_by_day)
    trace.input("weekly_contract_hours",  weekly_contract_hours)
    trace.input("daily_contract_hours",   daily_contract_hours)
    trace.input("weekly_paid_hours",      weekly_paid_hours)
    trace.input("monthly_standard_hours", monthly_standard_hours)
    trace.input("policy_version",         pv)

    def premium(hours: Decimal, key: str) -> Decimal:
        if not premium_applies:
            return Decimal("0")
        return amount_round(hours * hourly * Decimal(str(rates[key])), rules)

    base_pay   = amount_round((overtime + holiday_in + holiday_ov) * hourly, rules)
    p_overtime = premium(overtime, "overtime")
    p_night    = premium(night, "night")
    p_hol_in   = premium(holiday_in, "holiday_within_limit")
    p_hol_ov   = premium(holiday_ov, "holiday_over_limit")
    p_total    = p_overtime + p_night + p_hol_in + p_hol_ov
    total      = base_pay + p_total

    trace.step("weekly_basis_hours",     plain(basis.weekly_basis))
    trace.step("monthly_standard_hours", plain(basis.monthly_basis))
    trace.step("hourly_ordinary_wage",   plain(hourly))
    trace.step("holiday_within_limit",   plain(holiday_in))
    trace.step("holiday_over_limit",     plain(holiday_ov))
    trace.step("premium_applies",        premium_applies)
    trace.step("base_pay",               str(base_pay))
    trace.step("premium_total",          str(p_total))
    trace.output(str(total))

    resp: dict[str, Any] = {
        "hourly_ordinary_wage":   str(round_apply(hourly, 2, RoundingPolicy.HALF_UP)),
        "wage_unit":              wage_unit,
        "weekly_basis_hours":     plain(basis.weekly_basis),
        "monthly_standard_hours": plain(basis.monthly_basis),
        "premium_applies":        premium_applies,
        "hours": {
            "overtime":             plain(overtime),
            "night":                plain(night),
            "holiday_within_limit": plain(holiday_in),
            "holiday_over_limit":   plain(holiday_ov),
        },
        "base_pay": str(base_pay),
        "premiums": {
            "overtime":             str(p_overtime),
            "night":                str(p_night),
            "holiday_within_limit": str(p_hol_in),
            "holiday_over_limit":   str(p_hol_ov),
        },
        "premium_total":  str(p_total),
        "total_pay":      str(total),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return cast(OvertimePayResult, enrich_response(resp, policy_doc))
