"""Korean inheritance tax (상속세) calculator.

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


def _resolve_spouse_deduction(
    spouse_inheritance: Decimal,
    deductions:          dict[str, Any],
) -> Decimal:
    """Spouse deduction: min(actual inheritance, cap) with floor=min.

    상속세및증여세법 제19조 (배우자 상속공제).
    실제 상속액이 최소공제보다 작으면 최소공제, 아니면 min(실제, 최대).
    """
    min_d = D(str(deductions["spouse_min"]))
    max_d = D(str(deductions["spouse_max"]))
    if spouse_inheritance <= Decimal("0"):
        return Decimal("0")
    if spouse_inheritance < min_d:
        return min_d
    if spouse_inheritance > max_d:
        return max_d
    return spouse_inheritance


@REGISTRY.tool(
    namespace="tax",
    name="kr_inheritance",
    description=(
        "한국 상속세 계산 (상속세및증여세법 제26조). "
        "일괄공제·배우자공제 적용 후 누진세율 산출."
    ),
    version="1.0.0",
)
def tax_kr_inheritance(
    gross_estate:       str,
    spouse_inheritance: str,
    year:               int,
    use_lump_sum:       bool = True,
    rounding:           str  = "HALF_UP",
    decimals:           int  = 0,
) -> dict[str, Any]:
    """Calculate Korean inheritance tax.

    Args:
        gross_estate:       총 상속재산 (원)
        spouse_inheritance: 배우자가 실제로 받은 상속액 (원). 0이면 배우자 없음.
        year:               과세연도
        use_lump_sum:       True면 일괄공제 5억 사용. False면 기초공제 2억만 적용.
        rounding:           반올림 정책
        decimals:           소수점 자리수

    Returns:
        {gross_estate, deductions, taxable_base, tax,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_inheritance",
        formula=(
            "taxable = gross_estate - (lump_sum|basic) - spouse_deduction; "
            "tax = 누진세율 적용(taxable)"
        ),
    )

    policy_enum = _parse_rounding(rounding)
    gross       = D(gross_estate)
    spouse_amt  = D(spouse_inheritance)

    if gross < Decimal("0"):
        raise InvalidInputError("gross_estate는 0 이상이어야 합니다.")
    if spouse_amt < Decimal("0"):
        raise InvalidInputError("spouse_inheritance는 0 이상이어야 합니다.")
    if spouse_amt > gross:
        raise InvalidInputError("spouse_inheritance는 gross_estate를 초과할 수 없습니다.")

    policy_doc = policy_load("tax", "kr_inheritance", year)
    data       = policy_doc["data"]
    brackets   = data["brackets"]
    deductions = data["deductions"]
    pv         = policy_doc["policy_version"]

    trace.input("gross_estate",       gross_estate)
    trace.input("spouse_inheritance", spouse_inheritance)
    trace.input("year",               year)
    trace.input("use_lump_sum",       use_lump_sum)

    general_deduct = (
        D(str(deductions["lump_sum"])) if use_lump_sum
        else D(str(deductions["basic"]))
    )
    spouse_deduct  = _resolve_spouse_deduction(spouse_amt, deductions)

    taxable = gross - general_deduct - spouse_deduct
    if taxable < Decimal("0"):
        taxable = Decimal("0")

    tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        taxable, brackets, policy_enum, decimals
    )

    deduct_detail = {
        "general": str(general_deduct),
        "spouse":  str(spouse_deduct),
        "total":   str(general_deduct + spouse_deduct),
    }

    trace.step("deductions",   deduct_detail)
    trace.step("taxable_base", str(taxable))
    trace.step("breakdown",    breakdown)
    trace.output(str(tax))

    resp = {
        "gross_estate":   str(gross),
        "deductions":     deduct_detail,
        "taxable_base":   str(taxable),
        "tax":            str(tax),
        "effective_rate": str(eff_rate),
        "marginal_rate":  str(marginal_rate),
        "breakdown":      breakdown,
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
