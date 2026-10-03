"""US federal income tax calculator (tax_us.federal_income).

Tax year 2025 (filed 2026) IRS progressive brackets, 4 filing statuses.

Author: 최진호
Date: 2026-04-23
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


def _validate_filing_status(filing_status: str) -> None:
    if filing_status not in _VALID_FILING_STATUSES:
        raise InvalidInputError(
            f"유효하지 않은 filing_status: '{filing_status}'. "
            f"허용값: {sorted(_VALID_FILING_STATUSES)}"
        )


@REGISTRY.tool(
    namespace="tax_us",
    name="federal_income",
    description=(
        "미국 연방 소득세 계산 (IRS 2025 tax year, 7 progressive brackets × "
        "4 filing statuses). 표준공제(standard_deduction) 옵션 지원."
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
        taxable_income:           과세표준 (USD, Decimal string)
        filing_status:            신고 상태 (single/married_joint/married_separate/head_of_household)
        year:                     tax year (2025)
        apply_standard_deduction: True면 filing status별 표준공제 차감
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

    _validate_filing_status(filing_status)
    policy   = _parse_rounding(rounding)
    income   = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    policy_doc   = policy_load("tax_us", "federal_income", year)
    data         = policy_doc["data"]
    pv           = policy_doc["policy_version"]
    brackets     = data["brackets"][filing_status]
    std_ded_raw  = data["standard_deduction"][filing_status]
    std_ded      = D(str(std_ded_raw))

    trace.input("taxable_income",            taxable_income)
    trace.input("filing_status",             filing_status)
    trace.input("year",                      year)
    trace.input("apply_standard_deduction",  apply_standard_deduction)
    trace.input("rounding",                  rounding)
    trace.input("policy_version",            pv)

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
