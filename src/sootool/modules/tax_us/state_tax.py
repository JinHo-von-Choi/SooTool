"""US state income tax calculator (tax_us.state_tax).

Supports CA (FTB 9-bracket rate schedules plus the 1% Behavioral Health Services
Tax over 1,000,000), NY (9 brackets, with the tax benefit recapture worksheets for
New York AGI over the threshold), and TX (no income tax). Filing status dependent.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03
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
from sootool.modules.tax.progressive import (
    BracketBreakdown,
    _calc_progressive,
    _parse_rounding,
)
from sootool.modules.tax_us._brackets import schedule_tax
from sootool.modules.tax_us.federal_income import _validate_filing_status
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_SUPPORTED_STATES = frozenset({"CA", "NY", "TX"})

_RATIO_DECIMALS = 4


class StateRecapture(TypedDict):
    """세액 환수(recapture) 워크시트 적용 내역. method 에 따라 부가 키가 달라진다.

    method: schedule | flat | first_flat | first_phase_in | step
    """

    state_agi:           str
    schedule_tax:        str
    method:              str
    rate:                NotRequired[str]
    flat_tax:            NotRequired[str]
    ratio:               NotRequired[str]
    taxable_over:        NotRequired[str]
    recapture_base:      NotRequired[str]
    incremental_benefit: NotRequired[str]


class StateSurcharge(TypedDict):
    """주 가산세(CA Behavioral Health Services Tax) 적용 내역."""

    name:   str
    over:   str
    rate:   str
    base:   str
    amount: str


class TaxUsStateTaxResult(PolicyResult):
    tax:                            str
    effective_rate:                 str
    marginal_rate:                  str
    breakdown:                      list[BracketBreakdown]
    standard_deduction:             str
    taxable_income_after_deduction: str
    state:                          str
    filing_status:                  str
    has_income_tax:                 bool
    recapture:                      NotRequired[StateRecapture]
    surcharge:                      NotRequired[StateSurcharge]


def _validate_state(state: str) -> None:
    if state not in _SUPPORTED_STATES:
        raise InvalidInputError(
            f"지원하지 않는 state: '{state}'. "
            f"허용값: {sorted(_SUPPORTED_STATES)}"
        )


def _phase_in_ratio(excess: Decimal, width: Decimal) -> Decimal:
    """min(excess, width) / width 를 소수 넷째 자리에서 반올림한 비율(0~1)."""
    if excess <= Decimal("0"):
        return Decimal("0")
    capped = excess if excess < width else width
    return round_apply(capped / width, _RATIO_DECIMALS, RoundingPolicy.HALF_UP)


def _recapture_tax(
    taxable:      Decimal,
    agi:          Decimal,
    schedule_tax: Decimal,
    cfg:          dict[str, Any],
    schedule:     str,
) -> tuple[Decimal, dict[str, Any]]:
    """조정총소득이 임계액을 넘을 때 세액 계산 워크시트 규칙으로 세액을 구한다.

    규칙(NY IT-201-I 세액 계산 워크시트 구조):
    - agi <= agi_threshold: 스케줄 세액.
    - agi > flat_agi_over: 과세표준 x flat_rate.
    - 과세표준 <= first.taxable_upper: agi >= agi_threshold + phase_in_width 이면
      과세표준 x first.rate, 아니면 스케줄 세액 + (과세표준 x first.rate - 스케줄 세액) x 비율
      (비율 = (agi - agi_threshold) / phase_in_width).
    - 그 밖: 과세표준이 taxable_over 를 넘는 마지막 단계에서
      스케줄 세액 + recapture_base + incremental_benefit x 비율
      (비율 = min(agi - taxable_over, phase_in_width) / phase_in_width).

    Returns (반올림 전 세액, 계산 내역).
    """
    threshold = D(str(cfg["agi_threshold"]))
    width     = D(str(cfg["phase_in_width"]))
    flat_over = D(str(cfg["flat_agi_over"]))
    flat_rate = D(str(cfg["flat_rate"]))

    if agi <= threshold:
        return schedule_tax, {"method": "schedule"}

    if agi > flat_over:
        return taxable * flat_rate, {"method": "flat", "rate": str(flat_rate)}

    worksheet  = cfg["worksheets"][schedule]
    first      = worksheet["first"]
    first_cap  = D(str(first["taxable_upper"]))
    first_rate = D(str(first["rate"]))

    if taxable <= first_cap:
        flat_tax = taxable * first_rate
        if agi >= threshold + width:
            return flat_tax, {"method": "first_flat", "rate": str(first_rate)}
        ratio = _phase_in_ratio(agi - threshold, width)
        tax   = schedule_tax + (flat_tax - schedule_tax) * ratio
        return tax, {
            "method":   "first_phase_in",
            "rate":     str(first_rate),
            "flat_tax": str(flat_tax),
            "ratio":    str(ratio),
        }

    step: dict[str, Any] | None = None
    for candidate in worksheet["steps"]:
        if taxable > D(str(candidate["taxable_over"])):
            step = candidate
    if step is None:
        raise InvalidInputError(
            f"recapture 단계 설정이 과세표준 {taxable} 을 포함하지 않습니다."
        )

    over        = D(str(step["taxable_over"]))
    base        = D(str(step["recapture_base"]))
    incremental = D(str(step["incremental_benefit"]))
    ratio       = _phase_in_ratio(agi - over, width)
    tax         = schedule_tax + base + incremental * ratio
    return tax, {
        "method":              "step",
        "taxable_over":        str(over),
        "recapture_base":      str(base),
        "incremental_benefit": str(incremental),
        "ratio":               str(ratio),
    }


@REGISTRY.tool(
    namespace="tax_us",
    name="state_tax",
    description=(
        "미국 주 소득세를 계산한다(CA, NY, TX). 신고 유형별 누진 구간과 주별 표준공제를 반영하고 TX 는 소득세가 없어 0이다. "
        "NY 는 조정총소득(state_agi)이 107,650 을 넘으면 세액 환수(recapture) 워크시트를, CA 는 과세표준 1,000,000 초과분에 1% 가산세를 적용한다. "
        "금액은 USD Decimal 문자열이고 기본은 소수 둘째 자리 HALF_UP이다. "
        "연도별 지원 범위가 다르고(CA 2025), 지방세나 FICA 는 포함하지 않는다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_us_state_tax(
    taxable_income:           str,
    state:                    str,
    filing_status:            str,
    year:                     int,
    apply_standard_deduction: bool = False,
    rounding:                 str  = "HALF_UP",
    decimals:                 int  = 2,
    state_agi:                str  | None = None,
) -> TaxUsStateTaxResult:
    """Calculate US state income tax.

    Args:
        taxable_income:           과세표준 (USD, Decimal string). apply_standard_deduction=True 이면
                                  표준공제 전 금액(주 조정총소득)으로 해석한다.
        state:                    주 코드 (CA/NY/TX)
        filing_status:            single/married_joint/married_separate/head_of_household
                                  (qualifying_surviving_spouse 는 married_joint 표 적용)
        year:                     tax year (CA 2025, NY 2025·2026, TX 2025·2026)
        apply_standard_deduction: 주별 표준공제 적용 여부
        rounding:                 반올림 정책 (기본 HALF_UP)
        decimals:                 소수점 자리수 (기본 2, USD cents)
        state_agi:                주 조정총소득 (NY: New York AGI, IT-201 line 33). 정책에
                                  recapture 규칙이 있을 때만 쓴다. None 이면 taxable_income
                                  입력값을 쓴다(조정총소득은 과세표준 이상이므로 하한값).

    Returns:
        {tax, effective_rate, marginal_rate, breakdown, standard_deduction,
         taxable_income_after_deduction, state, filing_status, policy_version,
         has_income_tax, trace}. recapture 규칙이 있는 주는 recapture 항목
         {state_agi, schedule_tax, method, ...}, 가산세 규칙이 있는 주는 surcharge 항목
         {name, over, rate, base, amount} 을 더한다.
    """
    trace = CalcTrace(
        tool="tax_us.state_tax",
        formula=(
            "taxable_after = max(taxable_income - state_std_deduction, 0); "
            "tax = sum((min(taxable_after, upper) - lower) * rate for bracket) "
            "(구간 기준액 base 가 있으면 base + rate * (taxable_after - lower)); "
            "NY: AGI > 107,650 이면 recapture worksheet 적용; "
            "CA: 과세표준 1,000,000 초과분 1% 가산"
        ),
    )

    _validate_state(state)
    schedule = _validate_filing_status(filing_status)
    policy   = _parse_rounding(rounding)
    income   = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    agi = income if state_agi is None else D(state_agi)
    if agi < Decimal("0"):
        raise InvalidInputError("state_agi는 0 이상이어야 합니다.")

    key        = f"state_tax_{state.lower()}"
    policy_doc = policy_load("tax_us", key, year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    has_income_tax = bool(data.get("has_income_tax", True))

    trace.input("taxable_income",           taxable_income)
    trace.input("state",                    state)
    trace.input("filing_status",            filing_status)
    trace.input("year",                     year)
    trace.input("apply_standard_deduction", apply_standard_deduction)
    trace.input("rounding",                 rounding)
    trace.input("state_agi",                state_agi)
    trace.input("policy_version",           pv)
    trace.step("filing_status_schedule",    schedule)

    if not has_income_tax:
        # TX: no state income tax
        trace.step("has_income_tax", "false")
        trace.output("0")
        resp0: dict[str, Any] = {
            "tax":                            "0",
            "effective_rate":                 "0",
            "marginal_rate":                  "0",
            "breakdown":                      [],
            "standard_deduction":             "0",
            "taxable_income_after_deduction": str(income),
            "state":                          state,
            "filing_status":                  filing_status,
            "has_income_tax":                 False,
            "policy_version":                 pv,
            "trace":                          trace.to_dict(),
        }
        return cast(TaxUsStateTaxResult, enrich_response(resp0, policy_doc))

    brackets_map = data["brackets"]
    if schedule not in brackets_map:
        raise InvalidInputError(
            f"주 '{state}'는 filing_status '{filing_status}'를 지원하지 않습니다. "
            f"지원 목록: {sorted(brackets_map)}"
        )
    brackets = brackets_map[schedule]

    std_ded_map = data.get("standard_deduction", {})
    std_ded_raw = std_ded_map.get(schedule, 0)
    std_ded     = D(str(std_ded_raw))

    if apply_standard_deduction:
        taxable_after = income - std_ded
        if taxable_after < Decimal("0"):
            taxable_after = Decimal("0")
    else:
        taxable_after = income

    trace.step("standard_deduction",             str(std_ded if apply_standard_deduction else Decimal("0")))
    trace.step("taxable_income_after_deduction", str(taxable_after))

    _tax, _eff, marginal_rate, breakdown = _calc_progressive(
        taxable_after, brackets, policy, decimals
    )
    schedule_raw = schedule_tax(taxable_after, brackets)
    tax_raw      = schedule_raw
    trace.step("schedule_tax", str(schedule_raw))

    recapture_cfg  = data.get("recapture")
    recapture_info: dict[str, Any] | None = None
    if recapture_cfg is not None:
        tax_raw, detail = _recapture_tax(taxable_after, agi, schedule_raw, recapture_cfg, schedule)
        if detail["method"] == "flat":
            marginal_rate = D(detail["rate"])
        recapture_info = {
            "state_agi":    str(agi),
            "schedule_tax": str(schedule_raw),
            **detail,
        }
        trace.step("recapture", recapture_info)

    surcharge_cfg  = data.get("surcharge")
    surcharge_info: dict[str, Any] | None = None
    if surcharge_cfg is not None:
        sur_over   = D(str(surcharge_cfg["over"]))
        sur_rate   = D(str(surcharge_cfg["rate"]))
        sur_base   = taxable_after - sur_over if taxable_after > sur_over else Decimal("0")
        sur_amount = sur_base * sur_rate
        tax_raw    = tax_raw + sur_amount
        if sur_base > Decimal("0"):
            marginal_rate = marginal_rate + sur_rate
        surcharge_info = {
            "name":   str(surcharge_cfg.get("name", "")),
            "over":   str(sur_over),
            "rate":   str(sur_rate),
            "base":   str(sur_base),
            "amount": str(sur_amount),
        }
        trace.step("surcharge", surcharge_info)

    tax      = round_apply(tax_raw, decimals, policy)
    eff_rate = (
        round_apply(tax_raw / taxable_after, 8, RoundingPolicy.HALF_UP)
        if taxable_after > Decimal("0") else Decimal("0")
    )

    trace.step("breakdown", breakdown)
    trace.output(str(tax))

    resp: dict[str, Any] = {
        "tax":                            str(tax),
        "effective_rate":                 str(eff_rate),
        "marginal_rate":                  str(marginal_rate),
        "breakdown":                      breakdown,
        "standard_deduction":             str(std_ded if apply_standard_deduction else Decimal("0")),
        "taxable_income_after_deduction": str(taxable_after),
        "state":                          state,
        "filing_status":                  filing_status,
        "has_income_tax":                 True,
        "policy_version":                 pv,
        "trace":                          trace.to_dict(),
    }
    if recapture_info is not None:
        resp["recapture"] = recapture_info
    if surcharge_info is not None:
        resp["surcharge"] = surcharge_info
    return cast(TaxUsStateTaxResult, enrich_response(resp, policy_doc))
