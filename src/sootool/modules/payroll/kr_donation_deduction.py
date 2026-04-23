"""Korean donation tax credit (기부금 세액공제) calculator.

Author: 최진호
Date: 2026-04-24

소득세법 제59조의4 제4항 기부금 세액공제:
  - 1천만원 이하분: 15% 세액공제
  - 1천만원 초과분: 30% 세액공제
  - 법정기부금(legal): 한도 없음
  - 지정기부금(designated): 근로소득금액의 30% 한도
  - 정치자금(political) 10만원 이하: 100/110 환급세액공제(지방세포함 실효 약 90.9%)

입력은 법정·지정·정치자금 세 범주.
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

_POLITICAL_SMALL_CAP = Decimal("100000")  # 10만원


def _tiered_credit(
    qualifying: Decimal,
    threshold:  Decimal,
    rate_low:   Decimal,
    rate_high:  Decimal,
) -> Decimal:
    """1천만원 이하분 15%, 초과분 30% 구조."""
    if qualifying <= threshold:
        return qualifying * rate_low
    low_part  = threshold * rate_low
    high_part = (qualifying - threshold) * rate_high
    return low_part + high_part


@REGISTRY.tool(
    namespace="payroll",
    name="kr_donation_deduction",
    description=(
        "한국 기부금 세액공제(소득세법 §59의4) 계산. "
        "1천만원 이하 15%·초과 30%, 법정기부금 한도없음, 지정기부금 근로소득 30% 한도."
    ),
    version="1.0.0",
)
def payroll_kr_donation_deduction(
    earned_income:      str,
    year:               int,
    legal_donation:     str = "0",
    designated_donation: str = "0",
    political_donation: str = "0",
) -> dict[str, Any]:
    """Calculate donation tax credit.

    Args:
        earned_income:       근로소득금액(원). 지정기부금 30% 한도 산정 기준.
        year:                과세연도.
        legal_donation:      법정기부금(국가·지자체·재해 등), 한도 없음.
        designated_donation: 지정기부금(공익법인 등), 근로소득금액 30% 한도.
        political_donation:  정치자금 기부금.

    Returns:
        {earned_income, legal_credit, designated_credit, political_credit,
         political_small_credit, total_credit, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_donation_deduction",
        formula=(
            "각 범주별 공제대상액 산정 → 1천만원 이하 15%, 초과 30%; "
            "지정기부금은 근로소득금액 30% 한도; "
            "정치자금 10만원 이하는 100/110 환급세액공제"
        ),
    )

    ei   = D(earned_income)
    leg  = D(legal_donation)
    des  = D(designated_donation)
    pol  = D(political_donation)

    for name, val in [
        ("earned_income",       ei),
        ("legal_donation",      leg),
        ("designated_donation", des),
        ("political_donation",  pol),
    ]:
        if val < Decimal("0"):
            raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")

    policy_doc = policy_load("payroll", "kr_yearend_deductions", year)
    data       = policy_doc["data"]["donation"]
    pv         = policy_doc["policy_version"]

    rate_low  = D(str(data["rate_low"]))
    rate_high = D(str(data["rate_high"]))
    threshold = D(str(data["threshold"]))
    des_limit_rate = D(str(data["designated_limit_rate"]))
    pol_small_rate = D(str(data["political_credit_rate"]))

    trace.input("earned_income",       earned_income)
    trace.input("legal_donation",      legal_donation)
    trace.input("designated_donation", designated_donation)
    trace.input("political_donation",  political_donation)
    trace.input("year",                year)

    # 법정 기부금: 한도 없음
    legal_qualifying = leg
    legal_credit_raw = _tiered_credit(legal_qualifying, threshold, rate_low, rate_high)
    legal_credit     = round_apply(legal_credit_raw, 0, RoundingPolicy.DOWN)

    # 지정 기부금: 근로소득금액 × 30% 한도
    des_cap = ei * des_limit_rate
    des_qualifying = des if des <= des_cap else des_cap
    des_credit_raw = _tiered_credit(des_qualifying, threshold, rate_low, rate_high)
    designated_credit = round_apply(des_credit_raw, 0, RoundingPolicy.DOWN)

    # 정치자금: 10만원 이하는 환급세액공제, 초과분은 일반 15%/30%
    if pol <= _POLITICAL_SMALL_CAP:
        pol_small_raw    = pol * pol_small_rate
        political_small  = round_apply(pol_small_raw, 0, RoundingPolicy.DOWN)
        pol_remainder    = Decimal("0")
    else:
        pol_small_raw    = _POLITICAL_SMALL_CAP * pol_small_rate
        political_small  = round_apply(pol_small_raw, 0, RoundingPolicy.DOWN)
        pol_remainder    = pol - _POLITICAL_SMALL_CAP

    pol_rem_credit_raw = _tiered_credit(pol_remainder, threshold, rate_low, rate_high)
    political_credit   = round_apply(pol_rem_credit_raw, 0, RoundingPolicy.DOWN)

    total_credit = legal_credit + designated_credit + political_credit + political_small

    trace.step("legal_qualifying",       str(legal_qualifying))
    trace.step("legal_credit",           str(legal_credit))
    trace.step("designated_cap",         str(des_cap))
    trace.step("designated_qualifying",  str(des_qualifying))
    trace.step("designated_credit",      str(designated_credit))
    trace.step("political_small_credit", str(political_small))
    trace.step("political_remainder",    str(pol_remainder))
    trace.step("political_credit",       str(political_credit))
    trace.output(str(total_credit))

    resp: dict[str, Any] = {
        "earned_income":          str(ei),
        "legal_credit":           str(legal_credit),
        "designated_credit":      str(designated_credit),
        "political_small_credit": str(political_small),
        "political_credit":       str(political_credit),
        "total_credit":           str(total_credit),
        "policy_version":         pv,
        "trace":                  trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
