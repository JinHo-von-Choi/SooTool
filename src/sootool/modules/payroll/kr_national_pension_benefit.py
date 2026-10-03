"""Korean National Pension old-age benefit (국민연금 노령연금) estimator.

작성자: 최진호
작성일: 2026-10-03

기본연금액 (국민연금법 제51조제1항, 부칙 법률 제8541호 제20조·제27조, 부칙 법률 제20903호 제5조):
  [2.4(A+0.75B)xP1/P + 1.8(A+B)xP2/P + 1.5(A+B)xP3/P + ... + 1.245(A+B)xP20/P + 1.29(A+B)xP21/P]
  x (1 + 0.05 x n / 12),  n = 20년(240개월) 초과 가입월수
  A = 연금 수급 전 3년간 전체 가입자 평균소득월액의 평균액 (지급 개시 연도별 고시)
  B = 가입기간 기준소득월액을 재평가율로 연금 수급 전년도 현재가치로 환산한 평균
  P = 전체 가입월수, Pk = 비례상수 구간별 가입월수

노령연금액 (제63조제1항): 20년 이상이면 기본연금액, 10년 이상 20년 미만이면
  기본연금액 x (0.5 + 0.05 x (가입월수 - 120) / 12). 10년 미만은 노령연금 수급권이 없다(제61조).
조기노령연금 (제63조제2항): 앞당긴 1개월마다 0.5% 감액, 최대 60개월(70%).
연기연금 (제62조): 연기 1개월마다 0.6% 가산, 최대 60개월. 일부 연기는 50~90% 부분만 가산.
부양가족연금액 (제52조): 조기·연기 조정 뒤에 더한다.

B 입력 방식은 셋 중 하나다.
  b_value:         공단 예상연금 조회 등에서 확인한 B값을 그대로 쓴다.
  monthly_income:  현재 기준소득월액이 전 가입기간 동안 같았다고 보고 B로 쓴다(상·하한 적용).
  income_history:  연도별 기준소득월액과 가입월수에 고시 재평가율을 곱해 B를 산출한다.
b_value 와 monthly_income 방식은 가입이 contribution_end_year 12월까지 끊김 없이 이어졌다고 보고
가입월수를 연도에 거꾸로 배분해 구간별 비례상수를 정한다.

모델링하지 않는 범위: 군복무·출산·실업 크레딧, 소득활동에 따른 감액
(제63조의2), 지급 개시 뒤 물가변동률 조정(제51조제2항), 특수직종근로자 연령 특례.
금액은 원 미만 버림으로 표시하며 공단 실제 지급액의 끝수 처리와 다를 수 있다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, NotRequired, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy, truncate_to_unit
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO          = Decimal("0")
_ONE           = Decimal("1")
_TWELVE        = Decimal("12")
_MONTHS_A_YEAR = 12
_FINAL_YEARS_MONTHS = 60  # 제53조제1호: 가입자였던 최종 5년


class PensionPeriod(TypedDict):
    """비례상수 구간별 가입월수."""

    from_year: int
    to_year:   int | None
    constant:  str
    b_weight:  str
    months:    int


class KrNationalPensionBenefitResult(PolicyResult):
    input_mode:               str
    a_value:                  str
    b_value:                  str
    contribution_months:      int
    periods:                  list[PensionPeriod]
    weighted_amount:          str
    extension_factor:         str
    basic_pension_annual:     str
    payment_rate:             str
    old_age_pension_annual:   str
    claim_offset_months:      int
    deferral_ratio:           str
    adjustment_factor:        str
    adjusted_pension_annual:  str
    dependent_pension_annual: str
    total_pension_annual:     str
    monthly_pension:          str
    pension_cap_monthly:      str
    pension_capped:           bool
    income_capped:            NotRequired[bool]


def _floor_won(value: Decimal) -> Decimal:
    return round_apply(value, 0, RoundingPolicy.DOWN)


def _positive_amount(name: str, value: str) -> Decimal:
    amount = D(value)
    if amount <= _ZERO:
        raise InvalidInputError(f"{name}는 0보다 커야 합니다.")
    return amount


def _months_backward(total_months: int, end_year: int, first_year: int) -> dict[int, int]:
    """end_year 12월에서 거꾸로 total_months 를 연도별로 배분한다(연속 가입 가정)."""
    months_by_year: dict[int, int] = {}
    remaining = total_months
    year      = end_year
    while remaining > 0:
        if year < first_year:
            raise InvalidInputError(
                f"contribution_months({total_months})를 contribution_end_year({end_year})에서 거꾸로 배분하면 "
                f"{first_year}년 이전으로 넘어갑니다."
            )
        take                 = min(_MONTHS_A_YEAR, remaining)
        months_by_year[year] = take
        remaining           -= take
        year                -= 1
    return months_by_year


def _history_months_and_b(
    history:     list[dict[str, Any]],
    revaluation: dict[str, Any],
) -> tuple[dict[int, int], Decimal, Decimal]:
    """연도별 기준소득월액 이력에서 가입월수 배분, 재평가된 평균소득월액(B), 최종 5년 재평가 평균을 구한다."""
    if not history:
        raise InvalidInputError("income_history는 비어 있을 수 없습니다.")
    months_by_year: dict[int, int] = {}
    revalued_total = _ZERO
    revalued_by_year: dict[int, Decimal] = {}
    for index, entry in enumerate(history):
        if not isinstance(entry, dict) or set(entry) != {"year", "monthly_income", "months"}:
            raise InvalidInputError(
                f"income_history[{index}]는 year, monthly_income, months 세 키만 가진 객체여야 합니다."
            )
        year   = entry["year"]
        months = entry["months"]
        if isinstance(year, bool) or not isinstance(year, int):
            raise InvalidInputError(f"income_history[{index}].year는 정수여야 합니다.")
        if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= _MONTHS_A_YEAR:
            raise InvalidInputError(f"income_history[{index}].months는 1 이상 12 이하 정수여야 합니다.")
        if year in months_by_year:
            raise InvalidInputError(f"income_history에 {year}년이 두 번 있습니다.")
        rate = revaluation.get(str(year))
        if rate is None:
            raise InvalidInputError(
                f"income_history[{index}].year {year}의 재평가율이 고시에 없습니다 "
                f"({min(revaluation)}~{max(revaluation)}년만 가능)."
            )
        income = _positive_amount(f"income_history[{index}].monthly_income", str(entry["monthly_income"]))
        months_by_year[year] = months
        revalued_by_year[year] = income * D(str(rate))
        revalued_total        += income * Decimal(months) * D(str(rate))
    total_months = sum(months_by_year.values())
    recent_total, remaining = _ZERO, _FINAL_YEARS_MONTHS
    for year in sorted(months_by_year, reverse=True):
        take = min(months_by_year[year], remaining)
        recent_total += revalued_by_year[year] * Decimal(take)
        remaining    -= take
        if remaining == 0:
            break
    recent_months = _FINAL_YEARS_MONTHS - remaining
    return months_by_year, revalued_total / Decimal(total_months), recent_total / Decimal(recent_months)


def _periods(months_by_year: dict[int, int], regimes: list[dict[str, Any]]) -> list[PensionPeriod]:
    """연도별 가입월수를 비례상수 구간별로 합친다. 가입월수가 없는 구간은 뺀다."""
    first_year = int(regimes[0]["from_year"])
    early      = [y for y in months_by_year if y < first_year]
    if early:
        raise InvalidInputError(f"가입 연도는 {first_year}년 이후여야 합니다: {sorted(early)}")
    periods: list[PensionPeriod] = []
    for regime in regimes:
        lo = int(regime["from_year"])
        hi = regime["to_year"]
        months = sum(
            m for y, m in months_by_year.items()
            if y >= lo and (hi is None or y <= int(hi))
        )
        if months == 0:
            continue
        periods.append({
            "from_year": lo,
            "to_year":   None if hi is None else int(hi),
            "constant":  str(regime["constant"]),
            "b_weight":  str(regime["b_weight"]),
            "months":    months,
        })
    return periods


@REGISTRY.tool(
    namespace="payroll",
    name="kr_national_pension_benefit",
    description=(
        "국민연금 노령연금 예상액을 국민연금법 제51조 기본연금액 산식(A값, 구간별 비례상수 2.4~1.29, 20년 초과 연 5% 가산), "
        "제63조 가입기간별 지급률, 조기수령 월 0.5% 감액(최대 60개월), 연기 월 0.6% 가산(최대 60개월), 부양가족연금으로 계산한다. "
        "year 는 지급 개시 연도, 금액은 원 문자열, B는 b_value·monthly_income(현재 소득 유지 가정)·income_history(재평가율 적용) 중 하나. "
        "월 지급액은 10원 미만 버리고 제53조 최고한도(평균 기준소득월액)를 적용한다. 크레딧과 재직자 감액은 빠지므로 공단 확정 연금액 대용으로 쓰면 오용이다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_national_pension_benefit(
    year:                       int,
    contribution_months:        int | None             = None,
    b_value:                    str | None             = None,
    monthly_income:             str | None             = None,
    income_history:             list[dict[str, Any]] | None = None,
    contribution_end_year:      int | None             = None,
    claim_offset_months:        int                    = 0,
    deferral_ratio:             str                    = "1",
    dependent_spouse:           bool                   = False,
    dependent_children_parents: int                    = 0,
) -> KrNationalPensionBenefitResult:
    """Estimate the Korean National Pension old-age benefit.

    Args:
        year:                       연금 지급 개시 연도(A값·재평가율 적용 연도)
        contribution_months:        총 가입월수. b_value·monthly_income 방식에서 필수
        b_value:                    재평가된 가입기간 평균소득월액(B값, 원)
        monthly_income:             현재 기준소득월액(원). 전 가입기간 동일 소득 가정
        income_history:             [{"year": 2005, "monthly_income": "2500000", "months": 12}, ...]
        contribution_end_year:      b_value·monthly_income 방식의 마지막 가입 연도(기본 year - 1)
        claim_offset_months:        음수면 조기수령 개월수, 양수면 연기 개월수
        deferral_ratio:             연기 비율 0.5, 0.6, 0.7, 0.8, 0.9, 1 (기본 1, 전부 연기)
        dependent_spouse:           부양가족연금 대상 배우자 여부
        dependent_children_parents: 부양가족연금 대상 자녀·부모 수

    Returns:
        {input_mode, a_value, b_value, contribution_months, periods, basic_pension_annual,
         payment_rate, old_age_pension_annual, adjustment_factor, adjusted_pension_annual,
         dependent_pension_annual, total_pension_annual, monthly_pension, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_national_pension_benefit",
        formula=(
            "기본연금액 = sum(구간 상수 x (A + 가중치 x B) x 구간 월수 / P) x (1 + 0.05 x max(0, P - 240) / 12); "
            "노령연금 = 기본연금액 x (P >= 240 ? 1 : 0.5 + 0.05 x (P - 120) / 12); "
            "조기 = 노령연금 x (1 - 0.005 x 개월), 연기 = 노령연금 x ((1 - r) + r x (1 + 0.006 x 개월)); "
            "월 연금 = (조정 연금 + 부양가족연금) / 12"
        ),
    )

    modes = [name for name, value in (
        ("b_value", b_value), ("monthly_income", monthly_income), ("income_history", income_history),
    ) if value is not None]
    if len(modes) != 1:
        raise InvalidInputError("b_value, monthly_income, income_history 중 정확히 하나를 입력해야 합니다.")
    mode = modes[0]
    if mode == "income_history":
        if contribution_months is not None or contribution_end_year is not None:
            raise InvalidInputError(
                "income_history 방식에서는 contribution_months와 contribution_end_year를 입력하지 않습니다."
            )
    elif contribution_months is None:
        raise InvalidInputError(f"{mode} 방식에서는 contribution_months가 필요합니다.")
    if dependent_children_parents < 0:
        raise InvalidInputError("dependent_children_parents는 0 이상이어야 합니다.")

    # 기준소득월액 상·하한은 4대보험 정책에서 읽는다. 주 정책을 마지막에 읽어 영수증에 남긴다.
    ins_doc = policy_load("payroll", "kr_4insurance", year) if mode == "monthly_income" else None
    policy_doc = policy_load("payroll", "kr_national_pension_benefit", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    regimes: list[dict[str, Any]] = data["proportional_constants"]
    first_year = int(regimes[0]["from_year"])

    income_capped: bool | None = None
    recent_average: Decimal | None = None
    if mode == "income_history":
        months_by_year, b_amount, recent_average = _history_months_and_b(
            cast(list[dict[str, Any]], income_history), data["revaluation_rates"],
        )
    else:
        assert contribution_months is not None
        if contribution_months <= 0:
            raise InvalidInputError("contribution_months는 0보다 커야 합니다.")
        end_year       = contribution_end_year if contribution_end_year is not None else year - 1
        months_by_year = _months_backward(contribution_months, end_year, first_year)
        if mode == "b_value":
            b_amount = _positive_amount("b_value", cast(str, b_value))
        else:
            assert ins_doc is not None
            np_cfg   = ins_doc["data"]["national_pension"]
            income   = _positive_amount("monthly_income", cast(str, monthly_income))
            unit     = D(str(np_cfg.get("base_truncation_unit", 1)))
            floored  = round_apply(income / unit, 0, RoundingPolicy.DOWN) * unit
            lo       = D(str(np_cfg["base_min_monthly"]))
            hi       = D(str(np_cfg["base_max_monthly"]))
            b_amount = min(max(floored, lo), hi)
            income_capped = b_amount != floored

    total_months = sum(months_by_year.values())
    min_months   = int(data["minimum_months"])
    full_months  = int(data["full_benefit_months"])
    if total_months < min_months:
        raise InvalidInputError(
            f"가입월수 {total_months}개월은 노령연금 최소 가입기간 {min_months}개월(10년)에 못 미칩니다 "
            "(국민연금법 제61조). 노령연금 대신 반환일시금 대상입니다."
        )

    max_early = int(data["early_max_months"])
    max_defer = int(data["deferral_max_months"])
    if claim_offset_months < -max_early or claim_offset_months > max_defer:
        raise InvalidInputError(
            f"claim_offset_months는 -{max_early} 이상 {max_defer} 이하여야 합니다 (음수 조기, 양수 연기)."
        )
    allowed_ratios = [D(str(r)) for r in data["deferral_ratios"]]
    ratio = D(deferral_ratio)
    if ratio not in allowed_ratios:
        raise InvalidInputError(f"deferral_ratio는 {[str(r) for r in allowed_ratios]} 중 하나여야 합니다.")
    if ratio != _ONE and claim_offset_months <= 0:
        raise InvalidInputError("deferral_ratio는 연기(claim_offset_months > 0)할 때만 1 미만으로 지정합니다.")

    a_amount = D(str(data["a_value"]))
    periods  = _periods(months_by_year, regimes)
    p_total  = Decimal(total_months)

    weighted = sum(
        (D(p["constant"]) * (a_amount + D(p["b_weight"]) * b_amount) * Decimal(p["months"]) / p_total
         for p in periods),
        _ZERO,
    )
    extra_months     = max(0, total_months - full_months)
    extension_factor = _ONE + D(str(data["extension_rate_per_year"])) * Decimal(extra_months) / _TWELVE
    basic_annual     = weighted * extension_factor

    if total_months >= full_months:
        payment_rate = _ONE
    else:
        payment_rate = (
            D(str(data["partial_base_ratio"]))
            + D(str(data["partial_increment_per_year"])) * Decimal(total_months - min_months) / _TWELVE
        )
    old_age_annual = basic_annual * payment_rate

    if claim_offset_months < 0:
        adjustment = _ONE - D(str(data["early_reduction_per_month"])) * Decimal(-claim_offset_months)
    elif claim_offset_months > 0:
        bonus      = D(str(data["deferral_increment_per_month"])) * Decimal(claim_offset_months)
        adjustment = (_ONE - ratio) + ratio * (_ONE + bonus)
    else:
        adjustment = _ONE
    adjusted_annual = old_age_annual * adjustment

    dep_cfg          = data["dependent_annual"]
    dependent_annual = (
        (D(str(dep_cfg["spouse"])) if dependent_spouse else _ZERO)
        + D(str(dep_cfg["child_or_parent"])) * Decimal(dependent_children_parents)
    )
    # 제53조: 연금의 월별 지급액은 최종 5년 평균과 가입기간 전체 평균(재평가된 기준소득월액) 중 많은 금액을 넘지 못한다.
    pension_cap     = max(b_amount, recent_average) if recent_average is not None else b_amount
    pension_monthly = adjusted_annual / _TWELVE
    pension_capped  = pension_monthly > pension_cap
    if pension_capped:
        adjusted_annual = pension_cap * _TWELVE
    total_annual = adjusted_annual + dependent_annual
    unit         = D(str(data.get("monthly_truncation_unit", 1)))
    monthly      = truncate_to_unit(total_annual / _TWELVE, unit)

    trace.input("year",                       year)
    trace.input("input_mode",                 mode)
    trace.input("contribution_months",        contribution_months)
    trace.input("b_value",                    b_value)
    trace.input("monthly_income",             monthly_income)
    trace.input("income_history",             income_history)
    trace.input("contribution_end_year",      contribution_end_year)
    trace.input("claim_offset_months",        claim_offset_months)
    trace.input("deferral_ratio",             deferral_ratio)
    trace.input("dependent_spouse",           dependent_spouse)
    trace.input("dependent_children_parents", dependent_children_parents)

    trace.step("months_by_year",       {str(y): m for y, m in sorted(months_by_year.items())})
    trace.step("a_value",              str(a_amount))
    trace.step("b_value",              str(b_amount))
    trace.step("periods",              periods)
    trace.step("weighted_amount",      str(weighted))
    trace.step("extension_factor",     str(extension_factor))
    trace.step("basic_pension_annual", str(basic_annual))
    trace.step("payment_rate",         str(payment_rate))
    trace.step("adjustment_factor",    str(adjustment))
    trace.step("dependent_annual",     str(dependent_annual))
    if ins_doc is not None:
        trace.step("income_limits_policy_effective_date", ins_doc["policy_version"]["effective_date"])
    trace.output(str(monthly))

    resp: dict[str, Any] = {
        "input_mode":               mode,
        "a_value":                  str(a_amount),
        "b_value":                  str(b_amount),
        "contribution_months":      total_months,
        "periods":                  periods,
        "weighted_amount":          str(weighted),
        "extension_factor":         str(extension_factor),
        "basic_pension_annual":     str(_floor_won(basic_annual)),
        "payment_rate":             str(payment_rate),
        "old_age_pension_annual":   str(_floor_won(old_age_annual)),
        "claim_offset_months":      claim_offset_months,
        "deferral_ratio":           str(ratio),
        "adjustment_factor":        str(adjustment),
        "adjusted_pension_annual":  str(_floor_won(adjusted_annual)),
        "dependent_pension_annual": str(_floor_won(dependent_annual)),
        "total_pension_annual":     str(_floor_won(total_annual)),
        "monthly_pension":          str(monthly),
        "pension_cap_monthly":      str(_floor_won(pension_cap)),
        "pension_capped":           pension_capped,
        "policy_version":           pv,
        "trace":                    trace.to_dict(),
    }
    if income_capped is not None:
        resp["income_capped"] = income_capped
    return cast(KrNationalPensionBenefitResult, enrich_response(resp, policy_doc))
