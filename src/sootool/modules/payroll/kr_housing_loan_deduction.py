"""Korean long-term housing mortgage interest deduction calculator.

Author: 최진호
Date: 2026-04-24

소득세법 제52조 제4항 장기주택저당차입금 이자상환액 소득공제:
  - 상환기간 15년 이상, 고정금리 + 비거치식: 연 2,000만원 한도
  - 상환기간 15년 이상, 고정금리 OR 비거치식:   연 1,800만원 한도
  - 상환기간 15년 이상, 기타:                   연 500만원 한도
  - 상환기간 10~15년, 고정금리 OR 비거치식:     연 300만원 한도

소득공제(과세표준 차감)이므로 한계세율에 따라 실제 절세액은 다름.
본 도구는 공제 대상 이자상환액(한도 적용 후)을 반환한다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


def _resolve_limit_key(
    term_years:      int,
    is_fixed_rate:   bool,
    is_non_grace:    bool,
) -> str | None:
    """조건에 맞는 한도 키를 반환. 해당 없으면 None."""
    if term_years >= 15:
        if is_fixed_rate and is_non_grace:
            return "15+_fixed_nongrace"
        if is_fixed_rate or is_non_grace:
            return "15+_fixed_or_ng"
        return "15+_other"
    if 10 <= term_years < 15:
        if is_fixed_rate or is_non_grace:
            return "10_15_fixed_or_ng"
        return None   # 10~15년 기타는 공제 없음
    return None       # 10년 미만은 공제 대상 아님


@REGISTRY.tool(
    namespace="payroll",
    name="kr_housing_loan_deduction",
    description=(
        "한국 장기주택저당차입금 이자상환액 소득공제(소득세법 §52) 계산. "
        "상환기간·고정금리·비거치식 조건에 따른 한도 적용."
    ),
    version="1.0.0",
)
def payroll_kr_housing_loan_deduction(
    interest_paid:  str,
    term_years:     int,
    is_fixed_rate:  bool,
    is_non_grace:   bool,
    year:           int,
) -> dict[str, Any]:
    """Calculate housing mortgage interest deduction.

    Args:
        interest_paid:  당해 연도 이자상환액(원).
        term_years:     총 상환기간(년).
        is_fixed_rate:  고정금리 여부.
        is_non_grace:   비거치식 여부.
        year:           과세연도.

    Returns:
        {interest_paid, limit_key, limit, deductible_amount, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_housing_loan_deduction",
        formula=(
            "limit_key = f(term_years, fixed_rate, non_grace); "
            "deductible = min(interest_paid, limit); "
            "해당 없음 → deductible = 0"
        ),
    )

    paid = D(interest_paid)
    if paid < Decimal("0"):
        raise InvalidInputError("interest_paid는 0 이상이어야 합니다.")
    if term_years < 0:
        raise InvalidInputError("term_years는 0 이상이어야 합니다.")

    policy_doc = policy_load("payroll", "kr_yearend_deductions", year)
    data       = policy_doc["data"]["housing_loan_interest"]
    pv         = policy_doc["policy_version"]

    limits_cfg: dict[str, Any] = data["limits"]

    trace.input("interest_paid", interest_paid)
    trace.input("term_years",    term_years)
    trace.input("is_fixed_rate", is_fixed_rate)
    trace.input("is_non_grace",  is_non_grace)
    trace.input("year",          year)

    limit_key = _resolve_limit_key(term_years, is_fixed_rate, is_non_grace)
    if limit_key is None:
        limit      = Decimal("0")
        deductible = Decimal("0")
    else:
        limit      = D(str(limits_cfg[limit_key]))
        deductible = paid if paid <= limit else limit

    trace.step("limit_key",          limit_key if limit_key is not None else "none")
    trace.step("limit",              str(limit))
    trace.step("deductible_amount",  str(deductible))
    trace.output(str(deductible))

    resp: dict[str, Any] = {
        "interest_paid":      str(paid),
        "limit_key":          limit_key if limit_key is not None else "",
        "limit":              str(limit),
        "deductible_amount":  str(deductible),
        "policy_version":     pv,
        "trace":              trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
