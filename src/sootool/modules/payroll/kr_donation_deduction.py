"""Korean donation tax credit (기부금 세액공제) calculator.

Author: 최진호
Date: 2026-04-24
Modified: 2026-10-03

소득세법 제59조의4 제4항, 같은 법 시행령 제118조의7·제81조제4항, 조세특례제한법 제76조:
  - 특례기부금(legal)과 일반기부금(designated, religious)을 합한 금액의 15%,
    1천만원 초과분 30%. 특례기부금을 먼저 공제한다.
  - 한도 계산 순서(시행령 제81조제4항): 이월결손금 → 정치자금 → 고향사랑 → 특례 → 우리사주 → 일반.
    정치자금·고향사랑·특례기부금 한도 = 소득금액 - 이월결손금 - 선순위 기부금.
    일반기부금 한도 기준 = 소득금액 - 기부금등합계액(이월결손금·정치자금·고향사랑·특례·우리사주).
    종교단체 기부가 없으면 기준 × 30%, 있으면 기준 × 10% + min(기준 × 20%, 종교단체 외 기부액).
  - 정치자금: 10만원까지 110분의 100, 10만원 초과 금액의 15%(그 금액이 3천만원을 초과하는 분 25%).

고향사랑기부금과 우리사주조합기부금은 한도 계산 순서에만 반영하며 그 자체의 공제액은 계산하지 않는다.
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
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO = Decimal("0")


def _tiered_credit(
    qualifying: Decimal,
    threshold:  Decimal,
    rate_low:   Decimal,
    rate_high:  Decimal,
) -> Decimal:
    """분기선 이하분에 rate_low, 초과분에 rate_high 를 적용한다."""
    if qualifying <= threshold:
        return qualifying * rate_low
    low_part  = threshold * rate_low
    high_part = (qualifying - threshold) * rate_high
    return low_part + high_part


@REGISTRY.tool(
    namespace="payroll",
    name="kr_donation_deduction",
    description=(
        "한국 기부금 세액공제(소득세법 §59의4④, 조특법 §76) 계산. "
        "특례·일반기부금 합계 1천만원 이하 15%·초과 30%, 일반기부금 소득금액 30% 한도"
        "(종교단체 기부 시 10%+20%), 정치자금 10만원 이하 100/110·초과분 15%(3천만원 초과 25%)."
    ),
    version="1.1.0",
    policy=True,
)
def payroll_kr_donation_deduction(
    earned_income:       str,
    year:                int,
    legal_donation:      str = "0",
    designated_donation: str = "0",
    political_donation:  str = "0",
    religious_donation:  str = "0",
    carryover_loss:      str = "0",
    hometown_donation:   str = "0",
    esop_donation:       str = "0",
) -> dict[str, Any]:
    """Calculate donation tax credit.

    Args:
        earned_income:       근로소득금액(원). 기부금 한도 산정의 소득금액.
        year:                과세연도.
        legal_donation:      특례기부금(국가·지자체·재해 등).
        designated_donation: 종교단체 외 일반기부금(공익법인 등).
        political_donation:  정치자금 기부금.
        religious_donation:  종교단체 일반기부금.
        carryover_loss:      이월결손금(원).
        hometown_donation:   고향사랑기부금(한도 계산 순서 반영용).
        esop_donation:       우리사주조합기부금(한도 계산 순서 반영용).

    Returns:
        {earned_income, legal_limit, legal_qualifying, legal_credit,
         designated_limit, designated_qualifying, designated_credit,
         political_qualifying, political_small_credit, political_credit,
         total_credit, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_donation_deduction",
        formula=(
            "한도 순서: 이월결손금 → 정치자금 → 고향사랑 → 특례 → 우리사주 → 일반; "
            "특례 한도 = (소득금액 - 이월결손금 - 정치자금 - 고향사랑) × 100%; "
            "일반 한도 = 기준 × 30% (종교단체 기부 시 기준 × 10% + min(기준 × 20%, 종교단체 외)); "
            "공제 = (특례 + 일반) 1천만원 이하 15%, 초과 30% (특례 먼저); "
            "정치자금 10만원 이하 100/110, 초과 금액 15% (3천만원 초과분 25%)"
        ),
    )

    ei   = D(earned_income)
    leg  = D(legal_donation)
    des  = D(designated_donation)
    pol  = D(political_donation)
    rel  = D(religious_donation)
    loss = D(carryover_loss)
    home = D(hometown_donation)
    esop = D(esop_donation)

    for name, val in [
        ("earned_income",       ei),
        ("legal_donation",      leg),
        ("designated_donation", des),
        ("political_donation",  pol),
        ("religious_donation",  rel),
        ("carryover_loss",      loss),
        ("hometown_donation",   home),
        ("esop_donation",       esop),
    ]:
        if val < _ZERO:
            raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")

    policy_doc = policy_load("payroll", "kr_yearend_deductions", year)
    data       = policy_doc["data"]["donation"]
    pv         = policy_doc["policy_version"]

    rate_low        = D(str(data["rate_low"]))
    rate_high       = D(str(data["rate_high"]))
    threshold       = D(str(data["threshold"]))
    legal_lim_rate  = D(str(data["legal_limit_rate"]))
    des_limit_rate  = D(str(data["designated_limit_rate"]))
    rel_base_rate   = D(str(data["designated_religious_base_rate"]))
    rel_extra_rate  = D(str(data["designated_religious_extra_rate"]))
    pol_small_rate  = D(str(data["political_credit_rate"]))
    pol_small_cap   = D(str(data["political_small_cap"]))
    pol_rate_low    = D(str(data["political_rate_low"]))
    pol_rate_high   = D(str(data["political_rate_high"]))
    pol_threshold   = D(str(data["political_threshold"]))

    trace.input("earned_income",       earned_income)
    trace.input("legal_donation",      legal_donation)
    trace.input("designated_donation", designated_donation)
    trace.input("political_donation",  political_donation)
    trace.input("religious_donation",  religious_donation)
    trace.input("carryover_loss",      carryover_loss)
    trace.input("hometown_donation",   hometown_donation)
    trace.input("esop_donation",       esop_donation)
    trace.input("year",                year)

    # 정치자금·고향사랑·특례기부금: 소득금액 - 이월결손금 범위에서 순서대로 (시행령 제81조제4항제1호)
    remaining      = max(ei - loss, _ZERO)
    pol_qualifying = min(pol, remaining)
    remaining      = remaining - pol_qualifying
    home_used      = min(home, remaining)
    remaining      = remaining - home_used

    legal_limit      = remaining * legal_lim_rate
    legal_qualifying = min(leg, legal_limit)

    # 일반기부금: 기준 = 소득금액 - 기부금등합계액 (시행령 제81조제4항제3호)
    general_base = max(remaining - legal_qualifying - esop, _ZERO)
    if rel > _ZERO:
        designated_limit = general_base * rel_base_rate + min(general_base * rel_extra_rate, des)
    else:
        designated_limit = general_base * des_limit_rate
    designated_qualifying = min(des + rel, designated_limit)

    # 특례 + 일반 합계에 15%/30% 를 한 번 적용하고 특례기부금을 먼저 공제한다 (법 제59조의4제4항)
    legal_credit      = round_apply(
        _tiered_credit(legal_qualifying, threshold, rate_low, rate_high), 0, RoundingPolicy.DOWN
    )
    combined_credit   = round_apply(
        _tiered_credit(legal_qualifying + designated_qualifying, threshold, rate_low, rate_high),
        0,
        RoundingPolicy.DOWN,
    )
    designated_credit = combined_credit - legal_credit

    # 정치자금: 10만원까지 110분의 100, 초과 금액 15% (3천만원 초과분 25%) (조특법 제76조제1항)
    pol_small_part   = min(pol_qualifying, pol_small_cap)
    political_small  = round_apply(pol_small_part * pol_small_rate, 0, RoundingPolicy.DOWN)
    pol_remainder    = pol_qualifying - pol_small_part
    political_credit = round_apply(
        _tiered_credit(pol_remainder, pol_threshold, pol_rate_low, pol_rate_high), 0, RoundingPolicy.DOWN
    )

    total_credit = legal_credit + designated_credit + political_credit + political_small

    trace.step("political_qualifying",   str(pol_qualifying))
    trace.step("hometown_used",          str(home_used))
    trace.step("legal_limit",            str(legal_limit))
    trace.step("legal_qualifying",       str(legal_qualifying))
    trace.step("legal_credit",           str(legal_credit))
    trace.step("designated_base",        str(general_base))
    trace.step("designated_cap",         str(designated_limit))
    trace.step("designated_qualifying",  str(designated_qualifying))
    trace.step("designated_credit",      str(designated_credit))
    trace.step("political_small_credit", str(political_small))
    trace.step("political_remainder",    str(pol_remainder))
    trace.step("political_credit",       str(political_credit))
    trace.output(str(total_credit))

    resp: dict[str, Any] = {
        "earned_income":          str(ei),
        "legal_limit":            str(legal_limit),
        "legal_qualifying":       str(legal_qualifying),
        "legal_credit":           str(legal_credit),
        "designated_limit":       str(designated_limit),
        "designated_qualifying":  str(designated_qualifying),
        "designated_credit":      str(designated_credit),
        "political_qualifying":   str(pol_qualifying),
        "political_small_credit": str(political_small),
        "political_credit":       str(political_credit),
        "total_credit":           str(total_credit),
        "policy_version":         pv,
        "trace":                  trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
