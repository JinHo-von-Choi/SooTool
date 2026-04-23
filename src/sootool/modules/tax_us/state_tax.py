"""US state income tax calculator (tax_us.state_tax).

Supports CA (progressive, up to 10 brackets), NY (progressive, 9 brackets),
and TX (no income tax). Filing status dependent.

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
from sootool.modules.tax_us.federal_income import _validate_filing_status
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_SUPPORTED_STATES = frozenset({"CA", "NY", "TX"})


def _validate_state(state: str) -> None:
    if state not in _SUPPORTED_STATES:
        raise InvalidInputError(
            f"지원하지 않는 state: '{state}'. "
            f"허용값: {sorted(_SUPPORTED_STATES)}"
        )


@REGISTRY.tool(
    namespace="tax_us",
    name="state_tax",
    description=(
        "미국 주 소득세 계산 (CA·NY·TX). "
        "filing_status·주별 표준공제·누진구간 반영."
    ),
    version="1.0.0",
)
def tax_us_state_tax(
    taxable_income:           str,
    state:                    str,
    filing_status:            str,
    year:                     int,
    apply_standard_deduction: bool = False,
    rounding:                 str  = "HALF_UP",
    decimals:                 int  = 2,
) -> dict[str, Any]:
    """Calculate US state income tax.

    Args:
        taxable_income:           과세표준 (USD, Decimal string)
        state:                    주 코드 (CA/NY/TX)
        filing_status:            single/married_joint/married_separate/head_of_household
        year:                     tax year (2025)
        apply_standard_deduction: 주별 표준공제 적용 여부
        rounding:                 반올림 정책 (기본 HALF_UP)
        decimals:                 소수점 자리수 (기본 2, USD cents)

    Returns:
        {tax, effective_rate, marginal_rate, breakdown, standard_deduction,
         taxable_income_after_deduction, state, filing_status, policy_version,
         has_income_tax, trace}
    """
    trace = CalcTrace(
        tool="tax_us.state_tax",
        formula=(
            "taxable_after = max(taxable_income - state_std_deduction, 0); "
            "tax = sum((min(taxable_after, upper) - lower) * rate for bracket)"
        ),
    )

    _validate_state(state)
    _validate_filing_status(filing_status)
    policy = _parse_rounding(rounding)
    income = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

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
    trace.input("policy_version",           pv)

    if not has_income_tax:
        # TX: no state income tax
        trace.step("has_income_tax", "false")
        trace.output("0")
        resp0 = {
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
        return enrich_response(resp0, policy_doc)

    brackets_map = data["brackets"]
    if filing_status not in brackets_map:
        raise InvalidInputError(
            f"주 '{state}'는 filing_status '{filing_status}'를 지원하지 않습니다. "
            f"지원 목록: {sorted(brackets_map)}"
        )
    brackets = brackets_map[filing_status]

    std_ded_map = data.get("standard_deduction", {})
    std_ded_raw = std_ded_map.get(filing_status, 0)
    std_ded     = D(str(std_ded_raw))

    if apply_standard_deduction:
        taxable_after = income - std_ded
        if taxable_after < Decimal("0"):
            taxable_after = Decimal("0")
    else:
        taxable_after = income

    trace.step("standard_deduction",             str(std_ded if apply_standard_deduction else Decimal("0")))
    trace.step("taxable_income_after_deduction", str(taxable_after))

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
        "state":                          state,
        "filing_status":                  filing_status,
        "has_income_tax":                 True,
        "policy_version":                 pv,
        "trace":                          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
