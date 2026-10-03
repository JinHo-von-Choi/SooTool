"""Korean pension income tax (연금소득) withholding and pension income deduction calculator.

작성자: 최진호
작성일: 2026-10-03

사적연금(연금계좌) 인출 원천징수 (소득세법 제129조제1항):
  세액공제분·운용수익 연금수령 (제5호의2): 나이별 5%(70세 미만), 4%(80세 미만), 3%(80세 이상).
    종신계약은 3%(2025년 지급분 4%). 요건이 겹치면 낮은 세율.
  이연퇴직소득 연금수령 (제5호의3): 연금외수령 원천징수세율 × 70%(실제 수령연차 10년 이하),
    60%(20년 이하, 2025년 지급분은 10년 초과 전부), 50%(20년 초과, 2026년 지급분부터).
  세액공제분·운용수익 연금외수령 (제21조제1항제21호, 제129조제1항제6호나목): 기타소득 15%.
  개인지방소득세 특별징수: 원천징수 소득세 × 10% (지방세법 제103조의13제1항).

분리과세 판정 (제14조제3항제9호다목): 이연퇴직소득 연금수령분과 부득이한 인출분을 뺀 사적연금
  연간 합계가 1,500만원 이하이면 분리과세. 초과하면 종합과세 또는 15% 분리과세 선택 (제64조의4).

연금소득공제 (제47조의2): 총연금액(분리과세연금소득 제외)에 구간 공제, 한도 900만원.

세액은 원 미만 절사. 공적연금 간이세액표 원천징수, 종합소득세 산출과 선택 비교, 연금수령한도 계산,
연금계좌인출공제(제129조제8항, 2026-07-01 시행)는 계산하지 않는다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO = Decimal("0")
_ONE  = Decimal("1")


class PensionIncomeResult(PolicyResult):
    private_pension_amount:        str
    private_pension_rate:          str
    private_pension_tax:           str
    deferred_retirement_amount:    str
    deferred_retirement_ratio:     str
    deferred_retirement_rate:      str
    deferred_retirement_tax:       str
    non_pension_withdrawal_amount: str
    non_pension_withdrawal_rate:   str
    non_pension_withdrawal_tax:    str
    withholding_income_tax:        str
    withholding_local_tax:         str
    withholding_total:             str
    annual_private_pension_total:  str
    separate_taxation_threshold:   str
    separate_taxation_eligible:    bool
    separate_taxation_option_tax:  str
    total_pension_amount:          str
    pension_income_deduction:      str
    pension_income_amount:         str
    notes:                         list[str]


def _amount(name: str, value: str) -> Decimal:
    """금액 입력을 Decimal 로 바꾸고 음수를 거부한다."""
    amount = D(value)
    if amount < _ZERO:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


def _floor_won(value: Decimal) -> Decimal:
    return round_apply(value, 0, RoundingPolicy.DOWN)


def _age_rate(age: int, table: list[dict[str, Any]]) -> Decimal:
    """연금수령일 현재 나이에 해당하는 세율. 구간은 min_age 이상 max_age 미만."""
    for row in table:
        upper = row["max_age"]
        if age >= int(row["min_age"]) and (upper is None or age < int(upper)):
            return D(str(row["rate"]))
    raise InvalidInputError(f"age {age}에 해당하는 세율 구간이 없습니다.")


def _deferred_ratio(years: int, table: list[dict[str, Any]]) -> Decimal:
    """연금 실제 수령연차에 해당하는 비율. 구간은 max_years 이하."""
    for row in table:
        upper = row["max_years"]
        if upper is None or years <= int(upper):
            return D(str(row["ratio"]))
    raise InvalidInputError(f"actual_receipt_years {years}에 해당하는 비율 구간이 없습니다.")


def _pension_income_deduction(total: Decimal, cfg: dict[str, Any]) -> Decimal:
    """연금소득공제 (소득세법 제47조의2). over 초과 upto 이하 구간: base + (총연금액 - over) × rate."""
    if total <= _ZERO:
        return _ZERO
    for row in cfg["brackets"]:
        upto = row["upto"]
        if upto is None or total <= D(str(upto)):
            raw = D(str(row["base"])) + (total - D(str(row["over"]))) * D(str(row["rate"]))
            cap = D(str(cfg["cap"]))
            return _floor_won(raw if raw < cap else cap)
    raise InvalidInputError("연금소득공제 구간을 찾을 수 없습니다.")


@REGISTRY.tool(
    namespace="tax",
    name="kr_pension_income",
    description=(
        "한국 사적연금(연금계좌) 인출 원천징수, 분리과세 판정, 연금소득공제를 계산한다(소득세법 제129조, 제14조, 제47조의2). "
        "금액은 원 문자열이며 private_pension_amount 는 나이별 5·4·3%(종신 3%), deferred_retirement_amount 는 "
        "이연퇴직소득으로 연금외수령 세율의 70·60·50%, non_pension_withdrawal_amount 는 연금외수령 15%. "
        "지방소득세 10% 별도, 원 미만 절사. 사적연금 연 1,500만원 이하 분리과세. "
        "공적연금 간이세액표 원천징수는 계산하지 않으므로 공적연금 월 원천징수액 용도로 쓰면 오용이다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_pension_income(
    year:                          int,
    private_pension_amount:        str        = "0",
    age:                           int | None = None,
    lifetime_annuity:              bool       = False,
    deferred_retirement_amount:    str        = "0",
    deferred_retirement_tax_rate:  str | None = None,
    actual_receipt_years:          int | None = None,
    non_pension_withdrawal_amount: str        = "0",
    public_pension_amount:         str        = "0",
    annual_private_pension_total:  str | None = None,
) -> PensionIncomeResult:
    """Calculate private pension withholding, separate-taxation status and pension income deduction.

    Args:
        year:                          연금 지급(인출) 연도.
        private_pension_amount:        연금계좌 세액공제분·운용수익을 연금수령한 금액(원).
        age:                           연금수령일 현재 나이. private_pension_amount 가 있고 종신계약이 아니면 필수.
        lifetime_annuity:              사망일까지 연금수령하며 중도 해지할 수 없는 종신계약 여부.
        deferred_retirement_amount:    이연퇴직소득을 연금수령한 금액(원).
        deferred_retirement_tax_rate:  연금외수령 원천징수세율(비율, 예 "0.05"). 이연퇴직소득세를 이연퇴직소득으로
                                       나눈 값(시행령 제187조의3제2항). deferred_retirement_amount 가 있으면 필수.
        actual_receipt_years:          연금 실제 수령연차(1 이상). deferred_retirement_amount 가 있으면 필수.
        non_pension_withdrawal_amount: 세액공제분·운용수익을 연금외수령한 금액(원). 기타소득 15%.
        public_pension_amount:         과세 대상 공적연금 총연금액(원). 연금소득공제 계산에만 쓴다.
        annual_private_pension_total:  분리과세 판정 대상 사적연금 연간 합계(원). 이연퇴직소득 연금수령분과
                                       의료목적 등 부득이한 인출분은 넣지 않는다. 생략하면 private_pension_amount.

    Returns:
        PensionIncomeResult. 원천징수 세액, 분리과세 판정, 연금소득공제와 정책 출처.
    """
    trace = CalcTrace(
        tool="tax.kr_pension_income",
        formula=(
            "연금수령 원천징수 = floor(금액 × 나이별 세율 또는 종신계약 세율 중 낮은 것); "
            "이연퇴직소득 = floor(금액 × 연금외수령 원천징수세율 × 수령연차 비율); "
            "연금외수령 = floor(금액 × 15%); 지방소득세 = floor(각 소득세 × 10%); "
            "사적연금 연 합계 <= 1,500만원 → 분리과세, 초과 → 종합과세 또는 15% 선택; "
            "연금소득공제 = 구간 공제(한도 900만원)"
        ),
    )

    private     = _amount("private_pension_amount", private_pension_amount)
    deferred    = _amount("deferred_retirement_amount", deferred_retirement_amount)
    withdrawal  = _amount("non_pension_withdrawal_amount", non_pension_withdrawal_amount)
    public      = _amount("public_pension_amount", public_pension_amount)
    annual_priv = (
        _amount("annual_private_pension_total", annual_private_pension_total)
        if annual_private_pension_total is not None else private
    )

    if age is not None and not 0 <= age <= 150:
        raise InvalidInputError("age는 0 이상 150 이하이어야 합니다.")
    if private > _ZERO and age is None and not lifetime_annuity:
        raise InvalidInputError("private_pension_amount가 있으면 age를 입력해야 합니다(종신계약 제외).")

    deferred_tax_rate = _ZERO
    if deferred > _ZERO:
        if deferred_retirement_tax_rate is None or actual_receipt_years is None:
            raise InvalidInputError(
                "deferred_retirement_amount가 있으면 deferred_retirement_tax_rate와 actual_receipt_years를 입력해야 합니다."
            )
        deferred_tax_rate = D(deferred_retirement_tax_rate)
        if not _ZERO <= deferred_tax_rate <= _ONE:
            raise InvalidInputError("deferred_retirement_tax_rate는 0 이상 1 이하의 비율이어야 합니다.")
        if actual_receipt_years < 1:
            raise InvalidInputError("actual_receipt_years는 1 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_pension_income", year)
    data       = policy_doc["data"]

    trace.input("year",                          year)
    trace.input("private_pension_amount",        private_pension_amount)
    trace.input("age",                           age)
    trace.input("lifetime_annuity",              lifetime_annuity)
    trace.input("deferred_retirement_amount",    deferred_retirement_amount)
    trace.input("deferred_retirement_tax_rate",  deferred_retirement_tax_rate)
    trace.input("actual_receipt_years",          actual_receipt_years)
    trace.input("non_pension_withdrawal_amount", non_pension_withdrawal_amount)
    trace.input("public_pension_amount",         public_pension_amount)
    trace.input("annual_private_pension_total",  annual_private_pension_total)

    notes: list[str] = []

    candidates: list[Decimal] = []
    if age is not None:
        candidates.append(_age_rate(age, data["private_pension_age_rates"]))
    if lifetime_annuity:
        candidates.append(D(str(data["lifetime_annuity_rate"])))
    private_rate = min(candidates) if candidates else _ZERO
    private_tax  = _floor_won(private * private_rate)

    min_age = int(data["pension_receipt_min_age"])
    if private > _ZERO and age is not None and age < min_age:
        notes.append(
            f"연금수령은 {min_age}세 이후 개시가 요건이다(소득세법 시행령 제40조의2제3항제1호). "
            "의료목적 등 부득이한 인출이 아니면 연금외수령으로 입력한다."
        )

    deferred_ratio = (
        _deferred_ratio(actual_receipt_years, data["deferred_retirement_ratios"])
        if deferred > _ZERO and actual_receipt_years is not None else _ZERO
    )
    deferred_rate = deferred_tax_rate * deferred_ratio
    deferred_tax  = _floor_won(deferred * deferred_rate)

    withdrawal_rate = D(str(data["non_pension_withdrawal_rate"]))
    withdrawal_tax  = _floor_won(withdrawal * withdrawal_rate)

    local_ratio  = D(str(data["local_income_tax_ratio"]))
    income_total = private_tax + deferred_tax + withdrawal_tax
    local_total  = (
        _floor_won(private_tax * local_ratio)
        + _floor_won(deferred_tax * local_ratio)
        + _floor_won(withdrawal_tax * local_ratio)
    )

    threshold  = D(str(data["separate_taxation_threshold"]))
    eligible   = annual_priv <= threshold
    option_tax = _ZERO if eligible else _floor_won(annual_priv * D(str(data["separate_taxation_option_rate"])))
    if not eligible:
        notes.append(
            "사적연금 연간 합계가 분리과세 기준금액을 넘어 종합과세와 15% 분리과세 중 선택한다(소득세법 제64조의4). "
            "separate_taxation_option_tax 는 15% 선택 시 소득세이며 종합과세 세액은 계산하지 않는다."
        )

    total_pension = public + (_ZERO if eligible else annual_priv)
    deduction     = _pension_income_deduction(total_pension, data["pension_income_deduction"])
    income_amount = total_pension - deduction

    trace.step("private_pension_rate",        str(private_rate))
    trace.step("private_pension_tax",         str(private_tax))
    trace.step("deferred_retirement_ratio",   str(deferred_ratio))
    trace.step("deferred_retirement_tax",     str(deferred_tax))
    trace.step("non_pension_withdrawal_tax",  str(withdrawal_tax))
    trace.step("withholding_local_tax",       str(local_total))
    trace.step("separate_taxation_eligible",  eligible)
    trace.step("total_pension_amount",        str(total_pension))
    trace.step("pension_income_deduction",    str(deduction))
    trace.output(str(income_total + local_total))

    resp: dict[str, Any] = {
        "private_pension_amount":        str(private),
        "private_pension_rate":          str(private_rate),
        "private_pension_tax":           str(private_tax),
        "deferred_retirement_amount":    str(deferred),
        "deferred_retirement_ratio":     str(deferred_ratio),
        "deferred_retirement_rate":      str(deferred_rate),
        "deferred_retirement_tax":       str(deferred_tax),
        "non_pension_withdrawal_amount": str(withdrawal),
        "non_pension_withdrawal_rate":   str(withdrawal_rate),
        "non_pension_withdrawal_tax":    str(withdrawal_tax),
        "withholding_income_tax":        str(income_total),
        "withholding_local_tax":         str(local_total),
        "withholding_total":             str(income_total + local_total),
        "annual_private_pension_total":  str(annual_priv),
        "separate_taxation_threshold":   str(threshold),
        "separate_taxation_eligible":    eligible,
        "separate_taxation_option_tax":  str(option_tax),
        "total_pension_amount":          str(total_pension),
        "pension_income_deduction":      str(deduction),
        "pension_income_amount":         str(income_amount),
        "notes":                         notes,
        "policy_version":                policy_doc["policy_version"],
        "trace":                         trace.to_dict(),
    }
    return cast(PensionIncomeResult, enrich_response(resp, policy_doc))
