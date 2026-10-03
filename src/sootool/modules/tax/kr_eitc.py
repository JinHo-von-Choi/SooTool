"""Korean earned income tax credit (근로장려금) calculator.

Author: 최진호
Date: 2026-10-03

조세특례제한법 제10절의2 근로장려세제:
  - 신청자격 (법 제100조의3제1항): 부부 합산 연간 총소득 합계액이 총소득기준금액 미만
    (단독 2,200만원, 홑벌이 3,200만원, 맞벌이 4,400만원), 가구원 재산 합계액 2억4천만원 미만
  - 가구 구분 (법 제100조의3제5항): 맞벌이는 부부 각각의 총급여액 등이 300만원 이상
  - 총급여액 등 (법 제100조의3제5항제3호, 시행령 제100조의6): 사업소득 총수입금액 x 업종별 조정률
    + 근로소득(총급여액) + 종교인소득(총수입금액). 부동산임대업 소득은 제외
  - 연간 총소득 (시행령 제100조의3제1항): 총급여액 등의 구성 소득(부동산임대업 포함)
    + 이자·배당·연금소득 + 기타소득금액
  - 산정 (법 제100조의5): 배우자 총급여액 등 합산 후 시행령 별표 11 근로장려금 산정표 적용,
    재산 합계액 1억7천만원 이상이면 100분의 50
  - 결정 (법 제100조의7): 기한 후 신청은 100분의 95. 1만5천원 미만은 없음, 점증구간 10만원 미만은
    10만원, 점감구간 3만원 미만은 3만원

모델링하지 않는 범위: 자녀장려금, 반기 신청과 정산, 체납액 충당, 국적·부양자녀·직계존속 요건,
전문직 사업자와 월평균 근로소득 500만원 이상 상용근로자 제외 요건, 재산 평가.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, NotRequired, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_TABLE_COLUMNS: dict[str, int] = {"single": 2, "one_earner": 3, "dual_earner": 4}
_ZERO = Decimal("0")


class BusinessIncomeLine(TypedDict):
    """사업소득 한 건의 조정 내역."""

    earner:              str
    industry:            str
    revenue:             str
    adjustment_rate:     str
    adjusted_amount:     str
    counted_in_earnings: bool


class KrEitcResult(PolicyResult):
    year:                 int
    household_type:       str
    eligible:             bool
    ineligible_reasons:   list[str]
    applicant_earnings:   str
    spouse_earnings:      str
    total_earnings:       str
    total_income:         str
    total_income_limit:   str
    property_total:       str
    property_limit:       str
    business_lines:       list[BusinessIncomeLine]
    section:              str
    table_amount:         str
    table_bracket_lower:  NotRequired[str]
    table_bracket_upper:  NotRequired[str]
    property_reduced:     bool
    late_reduced:         bool
    reduced_amount:       str
    minimum_rule:         str | None
    eitc_amount:          str


def _non_negative(name: str, value: str) -> Decimal:
    """금액 입력을 Decimal 로 바꾸고 음수를 거부한다."""
    amount = D(value)
    if amount < _ZERO:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


def _business_lines(
    earner:   str,
    items:    list[dict[str, str]] | None,
    rates:    dict[str, Any],
    excluded: frozenset[str],
) -> list[BusinessIncomeLine]:
    """사업소득 총수입금액에 업종별 조정률을 곱한다 (시행령 제100조의3제1항제4호)."""
    lines: list[BusinessIncomeLine] = []
    for idx, item in enumerate(items or []):
        if not isinstance(item, dict) or "industry" not in item or "revenue" not in item:
            raise InvalidInputError(
                f"{earner} 사업소득 {idx}번 항목은 industry 와 revenue 를 가진 객체여야 합니다."
            )
        industry = item["industry"]
        if industry not in rates:
            raise InvalidInputError(f"industry 는 {sorted(rates)} 중 하나여야 합니다: {industry!r}")
        revenue = _non_negative(f"{earner} 사업소득 revenue", item["revenue"])
        rate    = D(str(rates[industry]))
        lines.append({
            "earner":              earner,
            "industry":            industry,
            "revenue":             str(revenue),
            "adjustment_rate":     str(rate),
            "adjusted_amount":     str(revenue * rate),
            "counted_in_earnings": industry not in excluded,
        })
    return lines


def _lookup_table(table: list[list[Any]], amount: Decimal, column: int) -> tuple[Decimal, list[Any] | None]:
    """별표 11 산정표에서 총급여액 등이 속한 구간의 금액. 표에 없거나 해당 없음이면 0."""
    for row in table:
        if D(str(row[0])) <= amount < D(str(row[1])):
            value = row[column]
            return (D(str(value)) if value is not None else _ZERO), row
    return _ZERO, None


@REGISTRY.tool(
    namespace="tax",
    name="kr_eitc",
    description=(
        "한국 근로장려금(조특법 §100의3·§100의5·§100의7) 산정. year 는 소득 귀속연도, 금액은 원 단위 숫자 "
        "문자열. 가구유형(single/one_earner/dual_earner)과 부부의 근로 총급여액, 사업 총수입금액(업종별 "
        "조정률 적용), 종교인소득, 재산 합계액으로 요건을 판정하고 시행령 별표 11 산정표 금액에 재산 1.7억원 "
        "이상 50%, 기한 후 95% 감액과 최소지급액 규칙을 적용한다. 산정표가 천원 단위라 별도 반올림은 없다. "
        "자녀장려금, 반기 신청, 체납 충당, 국적·부양자녀·전문직 요건은 판정하지 않는다. 사업소득에 필요경비를 "
        "뺀 소득금액을 넣는 것은 오용이다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_eitc(
    year:                    int,
    household_type:          str,
    property_total:          str,
    earned_income:           str                         = "0",
    business_income:         list[dict[str, str]] | None = None,
    religious_income:        str                         = "0",
    spouse_earned_income:    str                         = "0",
    spouse_business_income:  list[dict[str, str]] | None = None,
    spouse_religious_income: str                         = "0",
    other_income:            str                         = "0",
    late_application:        bool                        = False,
) -> KrEitcResult:
    """Calculate the Korean earned income tax credit for one household.

    Args:
        year:                    소득 귀속연도 (예: 2025년 소득분은 2025, 신청은 다음 해 5월).
        household_type:          single(단독), one_earner(홑벌이), dual_earner(맞벌이).
        property_total:          가구원 재산 합계액(원). 부채를 빼지 않은 시행령 평가액.
        earned_income:           신청자 근로소득 총급여액(비과세 제외, 원).
        business_income:         신청자 사업소득 목록. 각 항목 {"industry": 업종 코드, "revenue": 총수입금액}.
        religious_income:        신청자 종교인소득 총수입금액(원).
        spouse_earned_income:    배우자 근로소득 총급여액(원).
        spouse_business_income:  배우자 사업소득 목록 (형식은 business_income 과 같다).
        spouse_religious_income: 배우자 종교인소득 총수입금액(원).
        other_income:            부부의 이자·배당·연금소득 총수입금액과 기타소득금액 합계(원).
                                 총소득 요건 판정에만 쓴다.
        late_application:        신청기간 경과 후 6개월 이내 기한 후 신청 여부 (법 제100조의6제8항).

    Returns:
        요건 판정, 총급여액 등, 산정표 금액, 감액과 최소지급액 규칙을 거친 eitc_amount 와 trace.
    """
    trace = CalcTrace(
        tool="tax.kr_eitc",
        formula=(
            "총급여액 등 = Σ(사업 총수입금액 x 조정률, 부동산임대업 제외) + 근로 총급여액 + 종교인소득 (부부 합산); "
            "총소득 = 총급여액 등 구성 소득(부동산임대업 포함) + 이자·배당·연금·기타소득; "
            "요건: 총소득 < 총소득기준금액, 재산 < 2.4억; "
            "산정액 = 별표 11 산정표(총급여액 등) x (재산 1.7억 이상 0.5) x (기한 후 0.95); "
            "1.5만원 미만 0, 점증구간 10만원 미만 10만원, 점감구간 3만원 미만 3만원"
        ),
    )

    policy_doc = policy_load("tax", "kr_eitc", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    types: dict[str, Any] = data["household_types"]
    if household_type not in types:
        raise InvalidInputError(f"household_type 은 {sorted(types)} 중 하나여야 합니다.")
    cfg = types[household_type]

    prop     = _non_negative("property_total", property_total)
    earned   = _non_negative("earned_income", earned_income)
    relig    = _non_negative("religious_income", religious_income)
    s_earned = _non_negative("spouse_earned_income", spouse_earned_income)
    s_relig  = _non_negative("spouse_religious_income", spouse_religious_income)
    other    = _non_negative("other_income", other_income)

    rates    = data["business_adjustment_rates"]
    excluded = frozenset(data["earnings_excluded_industries"])
    lines    = (
        _business_lines("applicant", business_income, rates, excluded)
        + _business_lines("spouse", spouse_business_income, rates, excluded)
    )

    def _business_sum(earner: str, earnings_only: bool) -> Decimal:
        return sum(
            (D(ln["adjusted_amount"]) for ln in lines
             if ln["earner"] == earner and (ln["counted_in_earnings"] or not earnings_only)),
            _ZERO,
        )

    applicant_earnings = _business_sum("applicant", True) + earned + relig
    spouse_earnings    = _business_sum("spouse", True) + s_earned + s_relig
    total_earnings     = applicant_earnings + spouse_earnings
    total_income       = (
        _business_sum("applicant", False) + _business_sum("spouse", False)
        + earned + relig + s_earned + s_relig + other
    )

    min_each = D(str(data["dual_earner_min_each"]))
    spouse_has_income = s_earned > _ZERO or s_relig > _ZERO or any(ln["earner"] == "spouse" for ln in lines)
    if household_type == "single" and spouse_has_income:
        raise InvalidInputError("단독가구는 배우자가 없는 가구이므로 배우자 소득을 입력할 수 없습니다.")
    if household_type == "dual_earner" and (applicant_earnings < min_each or spouse_earnings < min_each):
        raise InvalidInputError(
            f"맞벌이 가구는 부부 각각의 총급여액 등이 {min_each}원 이상이어야 합니다 "
            f"(신청자 {applicant_earnings}, 배우자 {spouse_earnings}). 그 미만이면 one_earner 로 계산하세요."
        )
    if household_type == "one_earner" and applicant_earnings >= min_each and spouse_earnings >= min_each:
        raise InvalidInputError(
            f"부부 각각의 총급여액 등이 {min_each}원 이상이면 맞벌이 가구입니다. dual_earner 로 계산하세요."
        )

    trace.input("year",                    year)
    trace.input("household_type",          household_type)
    trace.input("property_total",          property_total)
    trace.input("earned_income",           earned_income)
    trace.input("business_income",         business_income)
    trace.input("religious_income",        religious_income)
    trace.input("spouse_earned_income",    spouse_earned_income)
    trace.input("spouse_business_income",  spouse_business_income)
    trace.input("spouse_religious_income", spouse_religious_income)
    trace.input("other_income",            other_income)
    trace.input("late_application",        late_application)

    income_limit   = D(str(cfg["total_income_limit"]))
    property_limit = D(str(data["property_limit"]))
    reasons: list[str] = []
    if total_income >= income_limit:
        reasons.append("total_income_not_below_limit")
    if prop >= property_limit:
        reasons.append("property_not_below_limit")
    eligible = not reasons

    phase_in_end = D(str(cfg["phase_in_end"]))
    plateau_end  = D(str(cfg["plateau_end"]))
    if total_earnings < phase_in_end:
        section = "phase_in"
    elif total_earnings < plateau_end:
        section = "plateau"
    else:
        section = "phase_out"

    table_amount, row = _lookup_table(data["calculation_table"], total_earnings, _TABLE_COLUMNS[household_type])
    if not eligible:
        table_amount = _ZERO

    property_reduced = eligible and prop >= D(str(data["property_reduction_threshold"]))
    late_reduced     = eligible and late_application
    reduced = table_amount
    if property_reduced:
        reduced = reduced * D(str(data["property_reduction_rate"]))
    if late_reduced:
        reduced = reduced * D(str(data["late_application_rate"]))
    reduced = round_apply(reduced, 0, RoundingPolicy.DOWN)

    floors      = data["minimum_award"]
    none_below  = D(str(floors["none_below"]))
    minimum_rule: str | None = None
    amount = reduced
    if not eligible or reduced == _ZERO:
        amount = _ZERO
    elif reduced < none_below:
        amount, minimum_rule = _ZERO, "below_minimum"
    elif section == "phase_in" and reduced < D(str(floors["phase_in_floor"])):
        amount, minimum_rule = D(str(floors["phase_in_floor"])), "phase_in_floor"
    elif section == "phase_out" and reduced < D(str(floors["phase_out_floor"])):
        amount, minimum_rule = D(str(floors["phase_out_floor"])), "phase_out_floor"

    trace.step("applicant_earnings", str(applicant_earnings))
    trace.step("spouse_earnings",    str(spouse_earnings))
    trace.step("total_earnings",     str(total_earnings))
    trace.step("total_income",       str(total_income))
    trace.step("total_income_limit", str(income_limit))
    trace.step("eligible",           eligible)
    trace.step("section",            section)
    trace.step("table_amount",       str(table_amount))
    trace.step("property_reduced",   property_reduced)
    trace.step("late_reduced",       late_reduced)
    trace.step("reduced_amount",     str(reduced))
    trace.step("minimum_rule",       minimum_rule)
    trace.output(str(amount))

    resp: dict[str, Any] = {
        "year":               year,
        "household_type":     household_type,
        "eligible":           eligible,
        "ineligible_reasons": reasons,
        "applicant_earnings": str(applicant_earnings),
        "spouse_earnings":    str(spouse_earnings),
        "total_earnings":     str(total_earnings),
        "total_income":       str(total_income),
        "total_income_limit": str(income_limit),
        "property_total":     str(prop),
        "property_limit":     str(property_limit),
        "business_lines":     lines,
        "section":            section,
        "table_amount":       str(table_amount),
        "property_reduced":   property_reduced,
        "late_reduced":       late_reduced,
        "reduced_amount":     str(reduced),
        "minimum_rule":       minimum_rule,
        "eitc_amount":        str(amount),
        "policy_version":     pv,
        "trace":              trace.to_dict(),
    }
    if row is not None:
        resp["table_bracket_lower"] = str(row[0])
        resp["table_bracket_upper"] = str(row[1])
    return cast(KrEitcResult, enrich_response(resp, policy_doc))
