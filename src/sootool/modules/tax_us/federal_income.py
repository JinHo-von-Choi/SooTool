"""US federal income tax calculator (tax_us.federal_income).

IRS progressive brackets per tax year (2025, 2026), 4 filing statuses.
Qualifying surviving spouse uses the married_joint schedule (IRC 1(j)(2)(A)).

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.tax.progressive import (
    _calc_progressive,
    _parse_rounding,
)
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_VALID_FILING_STATUSES = frozenset({
    "single",
    "married_joint",
    "married_separate",
    "head_of_household",
})


_FILING_STATUS_ALIASES: dict[str, str] = {
    "qualifying_surviving_spouse": "married_joint",
}


def _validate_filing_status(filing_status: str) -> str:
    """신고 유형을 검증하고 정책 표의 키를 돌려준다.

    생존 배우자(qualifying_surviving_spouse)는 연방 세율표, 표준공제, 장기 양도소득
    구간, NIIT 임계액(IRC 1411(b)(1))과 CA·NY 주 스케줄에서 공동 신고와 같은 표를
    쓰므로 married_joint 로 해석한다.
    """
    if filing_status in _FILING_STATUS_ALIASES:
        return _FILING_STATUS_ALIASES[filing_status]
    if filing_status not in _VALID_FILING_STATUSES:
        raise InvalidInputError(
            f"유효하지 않은 filing_status: '{filing_status}'. "
            f"허용값: {sorted(_VALID_FILING_STATUSES | set(_FILING_STATUS_ALIASES))}"
        )
    return filing_status


@REGISTRY.tool(
    namespace="tax_us",
    name="federal_income",
    description=(
        "미국 연방 소득세 계산 (IRS 2025·2026 tax year, 7 progressive brackets × "
        "4 filing statuses, 생존 배우자는 공동 신고 표). 표준공제 옵션을 켜면 "
        "taxable_income 을 조정총소득(AGI)으로 보고 표준공제를 뺀다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_us_federal_income(
    taxable_income:           str,
    filing_status:            str,
    year:                     int,
    apply_standard_deduction: bool = False,
    rounding:                 str  = "HALF_UP",
    decimals:                 int  = 2,
) -> dict[str, Any]:
    """Calculate US federal income tax using IRS progressive brackets.

    Args:
        taxable_income:           과세표준 (USD, Decimal string). apply_standard_deduction=True 이면
                                  표준공제 전 금액, 곧 조정총소득(AGI, IRC 62)으로 해석한다.
                                  이미 공제를 뺀 과세표준을 넣을 때는 False 로 둔다.
        filing_status:            신고 상태 (single/married_joint/married_separate/head_of_household,
                                  qualifying_surviving_spouse 는 married_joint 표 적용)
        year:                     tax year (2025, 2026)
        apply_standard_deduction: True면 filing status별 표준공제 차감 (IRC 63(c))
        rounding:                 반올림 정책 (기본 HALF_UP)
        decimals:                 소수점 자리수 (기본 2, USD cents)

    Returns:
        {tax, effective_rate, marginal_rate, breakdown, standard_deduction,
         taxable_income_after_deduction, filing_status, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax_us.federal_income",
        formula=(
            "taxable_after = max(taxable_income - standard_deduction, 0); "
            "tax = sum((min(taxable_after, upper) - lower) * rate for bracket)"
        ),
    )

    schedule = _validate_filing_status(filing_status)
    policy   = _parse_rounding(rounding)
    income   = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    policy_doc   = policy_load("tax_us", "federal_income", year)
    data         = policy_doc["data"]
    pv           = policy_doc["policy_version"]
    brackets     = data["brackets"][schedule]
    std_ded_raw  = data["standard_deduction"][schedule]
    std_ded      = D(str(std_ded_raw))

    trace.input("taxable_income",            taxable_income)
    trace.input("filing_status",             filing_status)
    trace.input("year",                      year)
    trace.input("apply_standard_deduction",  apply_standard_deduction)
    trace.input("rounding",                  rounding)
    trace.input("policy_version",            pv)
    trace.step("filing_status_schedule",     schedule)

    if apply_standard_deduction:
        taxable_after = income - std_ded
        if taxable_after < Decimal("0"):
            taxable_after = Decimal("0")
    else:
        taxable_after = income

    trace.step("standard_deduction",              str(std_ded if apply_standard_deduction else Decimal("0")))
    trace.step("taxable_income_after_deduction",  str(taxable_after))

    tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        taxable_after, brackets, policy, decimals
    )

    trace.step("breakdown", breakdown)
    trace.output(str(tax))

    resp = {
        "tax":                            str(tax),
        "effective_rate":                 str(eff_rate),
        "marginal_rate":                  str(marginal_rate),
        "breakdown":                      breakdown,
        "standard_deduction":             str(std_ded if apply_standard_deduction else Decimal("0")),
        "taxable_income_after_deduction": str(taxable_after),
        "filing_status":                  filing_status,
        "policy_version":                 pv,
        "trace":                          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
