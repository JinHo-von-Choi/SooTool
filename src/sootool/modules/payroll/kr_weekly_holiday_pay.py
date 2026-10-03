"""Korean weekly paid holiday allowance (주휴수당) calculator.

Author: 최진호
Date: 2026-10-03

주휴수당 (근로기준법 제55조제1항, 제18조제3항, 시행령 제30조제1항, 별표 2):

  1. 4주 평균 1주 소정근로시간이 15시간 미만이면 주휴를 적용하지 않는다 (법 제18조제3항).
  2. 1주 소정근로일을 개근하고 그 1주간 근로관계가 존속해야 한다
     (시행령 제30조제1항, 고용노동부 임금근로시간과-1736, 2021.8.4.).
  3. 주휴시간 = 1일 소정근로시간 = min(1주 소정근로시간 / 통상 근로자 1주 소정근로일 수, 8)
     (별표 2 제2호나목: 4주 소정근로시간 / 4주 통상 근로자 총 소정근로일 수, 법 제50조제2항)
  4. 주휴수당 = 주휴시간 × 시간급 통상임금, 원 미만 올림

같은 모듈의 시간 환산 함수는 연장·야간·휴일수당과 최저임금 검토 도구가 함께 쓴다:

  1주 기준시간 = 1주 소정근로시간 + 1주 유급 처리 시간(주휴 등)
  월 기준시간  = 1주 기준시간 × 365 / 7 / 12  (근로기준법 시행령 제6조제2항제4호,
                                              최저임금법 시행령 제5조제1항제3호)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, NamedTuple, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

WAGE_UNITS: tuple[str, ...] = ("hourly", "daily", "weekly", "monthly")


class WeeklyHolidayPayResult(PolicyResult):
    eligible:              bool
    ineligible_reasons:    list[str]
    weekly_contract_hours: str
    holiday_hours:         str
    hourly_ordinary_wage:  str
    weekly_holiday_pay:    str


class HourBasis(NamedTuple):
    """시간급 환산에 쓰는 1주·1개월 기준시간."""

    weekly_contract: Decimal
    weekly_paid:     Decimal
    weekly_basis:    Decimal
    monthly_basis:   Decimal


def plain(value: Decimal) -> str:
    """Decimal 을 지수 표기 없는 문자열로 바꾼다."""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def non_negative(name: str, value: str) -> Decimal:
    """숫자 문자열을 Decimal 로 바꾸고 유한한 0 이상 값만 받는다."""
    number = D(value)
    if not number.is_finite():
        raise InvalidInputError(f"{name}는 유한한 숫자여야 합니다.")
    if number < Decimal("0"):
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return number


def positive(name: str, value: str) -> Decimal:
    """숫자 문자열을 Decimal 로 바꾸고 0 보다 큰 값만 받는다."""
    number = non_negative(name, value)
    if number == Decimal("0"):
        raise InvalidInputError(f"{name}는 0보다 커야 합니다.")
    return number


def amount_round(value: Decimal, rules: dict[str, Any]) -> Decimal:
    """정책의 금액 반올림 규칙(원 단위)을 적용한다.

    나눗셈 뒤 곱셈에서 생기는 28자리 정밀도 끝자리 오차가 올림을 1원 바꾸지 않도록 소수 6자리에서
    먼저 반올림한다.
    """
    spec   = rules["amount_rounding"]
    steady = round_apply(value, 6, RoundingPolicy.HALF_UP)
    return round_apply(steady, int(spec["decimals"]), RoundingPolicy(spec["policy"]))


def weekly_holiday_hours(
    weekly_contract_hours:      Decimal,
    regular_worker_weekly_days: int,
    rules:                      dict[str, Any],
) -> Decimal:
    """주휴로 유급 처리되는 1일 소정근로시간. 15시간 미만이면 0."""
    spec = rules["weekly_holiday"]
    if weekly_contract_hours < Decimal(str(spec["min_weekly_contract_hours"])):
        return Decimal("0")
    daily = weekly_contract_hours / Decimal(regular_worker_weekly_days)
    cap   = Decimal(str(spec["daily_hours_cap"]))
    return daily if daily < cap else cap


def monthly_hours(weekly_basis: Decimal, rules: dict[str, Any]) -> Decimal:
    """1주 기준시간을 월 기준시간으로 환산하고 정책의 자릿수로 반올림한다."""
    spec = rules["monthly_hours"]
    raw  = (
        weekly_basis
        * Decimal(str(spec["days_per_year"]))
        / Decimal(str(spec["days_per_week"]))
        / Decimal(str(spec["months_per_year"]))
    )
    return round_apply(raw, int(spec["round_decimals"]), RoundingPolicy(spec["rounding"]))


def resolve_hour_basis(
    weekly_contract_hours:  str,
    weekly_paid_hours:      str | None,
    monthly_standard_hours: str | None,
    rules:                  dict[str, Any],
) -> HourBasis:
    """1주 소정근로시간과 선택 입력으로 1주·월 기준시간을 정한다.

    유급 처리 시간을 주지 않으면 주휴시간(통상 근로자 주 5일 기준)을 쓰고, 월 기준시간을 주지 않으면
    1주 기준시간에서 환산한다.
    """
    weekly = positive("weekly_contract_hours", weekly_contract_hours)
    if weekly > Decimal("168"):
        raise InvalidInputError("weekly_contract_hours는 168 이하여야 합니다.")
    if weekly_paid_hours is None:
        paid = weekly_holiday_hours(weekly, 5, rules)
    else:
        paid = non_negative("weekly_paid_hours", weekly_paid_hours)
    basis = weekly + paid
    if monthly_standard_hours is None:
        month = monthly_hours(basis, rules)
    else:
        month = positive("monthly_standard_hours", monthly_standard_hours)
    return HourBasis(weekly, paid, basis, month)


def hourly_from_wage(
    amount:               Decimal,
    wage_unit:            str,
    daily_contract_hours: str | None,
    basis:                HourBasis,
) -> Decimal:
    """일급·주급·월급을 시간급으로 환산한다 (근로기준법 시행령 제6조제2항, 최저임금법 시행령 제5조제1항)."""
    if wage_unit == "hourly":
        return amount
    if wage_unit == "daily":
        if daily_contract_hours is None:
            raise InvalidInputError("wage_unit이 daily이면 daily_contract_hours가 필요합니다.")
        daily = positive("daily_contract_hours", daily_contract_hours)
        if daily > Decimal("24"):
            raise InvalidInputError("daily_contract_hours는 24 이하여야 합니다.")
        return amount / daily
    if wage_unit == "weekly":
        return amount / basis.weekly_basis
    if wage_unit == "monthly":
        return amount / basis.monthly_basis
    raise InvalidInputError(f"wage_unit은 {', '.join(WAGE_UNITS)} 중 하나여야 합니다: {wage_unit!r}")


def check_weekdays(value: int) -> int:
    """통상 근로자의 1주 소정근로일 수(1~7 정수)를 확인한다."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 7:
        raise InvalidInputError("regular_worker_weekly_days는 1 이상 7 이하의 정수여야 합니다.")
    return value


@REGISTRY.tool(
    namespace="payroll",
    name="kr_weekly_holiday_pay",
    description=(
        "한국 주휴수당을 계산한다(근로기준법 제55조제1항·제18조제3항, 시행령 제30조·별표 2). "
        "weekly_contract_hours 는 4주 평균 1주 소정근로시간, hourly_ordinary_wage 는 시간급 통상임금(원)이다. "
        "15시간 이상, 소정근로일 개근, 그 주까지 근로관계 존속이면 주휴시간 = min(주 소정근로시간 / 통상 근로자 주 소정근로일 수, 8)에 "
        "시급을 곱하고 원 미만은 올린다. 시급제·일급제 근로자용이며 주휴분이 이미 포함된 월급에 더하면 이중 계산이다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_weekly_holiday_pay(
    weekly_contract_hours:      str,
    hourly_ordinary_wage:       str,
    year:                       int,
    perfect_attendance:         bool = True,
    employed_through_week:      bool = True,
    regular_worker_weekly_days: int  = 5,
) -> WeeklyHolidayPayResult:
    """Calculate Korean weekly paid holiday allowance (주휴수당).

    Args:
        weekly_contract_hours:      4주 평균 1주 소정근로시간(시간, Decimal 문자열)
        hourly_ordinary_wage:       시간급 통상임금(원)
        year:                       적용 연도
        perfect_attendance:         그 주 소정근로일 개근 여부
        employed_through_week:      그 1주간 근로관계가 존속했는지 여부
        regular_worker_weekly_days: 같은 업무 통상 근로자의 1주 소정근로일 수(기본 5)

    Returns:
        {eligible, ineligible_reasons, weekly_contract_hours, holiday_hours,
         hourly_ordinary_wage, weekly_holiday_pay, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_weekly_holiday_pay",
        formula=(
            "주휴시간 = min(주 소정근로시간 / 통상 근로자 주 소정근로일 수, 8) "
            "(주 소정근로시간 15 이상, 개근, 근로관계 존속); "
            "주휴수당 = ceil(주휴시간 × 시간급 통상임금)"
        ),
    )

    weekly = non_negative("weekly_contract_hours", weekly_contract_hours)
    if weekly > Decimal("168"):
        raise InvalidInputError("weekly_contract_hours는 168 이하여야 합니다.")
    wage = non_negative("hourly_ordinary_wage", hourly_ordinary_wage)
    days = check_weekdays(regular_worker_weekly_days)

    policy_doc = policy_load("payroll", "kr_labor_pay", year)
    rules      = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("weekly_contract_hours",      weekly_contract_hours)
    trace.input("hourly_ordinary_wage",       hourly_ordinary_wage)
    trace.input("year",                       year)
    trace.input("perfect_attendance",         perfect_attendance)
    trace.input("employed_through_week",      employed_through_week)
    trace.input("regular_worker_weekly_days", days)
    trace.input("policy_version",             pv)

    threshold = Decimal(str(rules["weekly_holiday"]["min_weekly_contract_hours"]))
    reasons: list[str] = []
    if weekly < threshold:
        reasons.append(f"4주 평균 1주 소정근로시간 {plain(threshold)}시간 미만(근로기준법 제18조제3항)")
    if not perfect_attendance:
        reasons.append("1주 소정근로일 미개근(근로기준법 시행령 제30조제1항)")
    if not employed_through_week:
        reasons.append("1주간 근로관계 미존속")
    eligible = not reasons

    hours = weekly_holiday_hours(weekly, days, rules) if eligible else Decimal("0")
    pay   = amount_round(hours * wage, rules)

    trace.step("eligible",      eligible)
    trace.step("reasons",       reasons)
    trace.step("holiday_hours", plain(hours))
    trace.step("raw_pay",       plain(hours * wage))
    trace.output(str(pay))

    resp: dict[str, Any] = {
        "eligible":              eligible,
        "ineligible_reasons":    reasons,
        "weekly_contract_hours": plain(weekly),
        "holiday_hours":         plain(hours),
        "hourly_ordinary_wage":  plain(wage),
        "weekly_holiday_pay":    str(pay),
        "policy_version":        pv,
        "trace":                 trace.to_dict(),
    }
    return cast(WeeklyHolidayPayResult, enrich_response(resp, policy_doc))
