"""Korean gift tax (증여세) calculator.

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

_ALLOWED_RELATIONSHIPS = frozenset([
    "spouse",
    "lineal_ascendant",
    "lineal_ascendant_minor",
    "lineal_descendant",
    "other_relative",
    "other",
])


@REGISTRY.tool(
    namespace="tax",
    name="kr_gift",
    description=(
        "한국 증여세 계산 (상속세및증여세법 제56조). "
        "수증자 관계별 증여재산공제(10년 합산 기준) 적용 후 누진세율."
    ),
    version="1.0.0",
)
def tax_kr_gift(
    gift_amount:  str,
    relationship: str,
    year:         int,
    rounding:     str = "HALF_UP",
    decimals:     int = 0,
) -> dict[str, Any]:
    """Calculate Korean gift tax.

    Args:
        gift_amount:  증여재산가액 (원)
        relationship: 수증자 관계 (spouse | lineal_ascendant |
                      lineal_ascendant_minor | lineal_descendant |
                      other_relative | other)
        year:         과세연도
        rounding:     반올림 정책
        decimals:     소수점 자리수

    Returns:
        {gift_amount, deduction, taxable_base, tax,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_gift",
        formula=(
            "taxable = gift_amount - 관계별 공제; "
            "tax = 누진세율 적용(taxable)"
        ),
    )

    if relationship not in _ALLOWED_RELATIONSHIPS:
        raise InvalidInputError(
            f"지원하지 않는 relationship: '{relationship}'. "
            f"허용값: {sorted(_ALLOWED_RELATIONSHIPS)}"
        )

    policy_enum = _parse_rounding(rounding)
    amount      = D(gift_amount)

    if amount < Decimal("0"):
        raise InvalidInputError("gift_amount는 0 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_gift", year)
    data       = policy_doc["data"]
    brackets   = data["brackets"]
    ded_table  = data["relationship_deduction"]
    pv         = policy_doc["policy_version"]

    trace.input("gift_amount",  gift_amount)
    trace.input("relationship", relationship)
    trace.input("year",         year)

    deduction = D(str(ded_table[relationship]))
    taxable   = amount - deduction
    if taxable < Decimal("0"):
        taxable = Decimal("0")

    tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        taxable, brackets, policy_enum, decimals
    )

    trace.step("deduction",    str(deduction))
    trace.step("taxable_base", str(taxable))
    trace.step("breakdown",    breakdown)
    trace.output(str(tax))

    resp = {
        "gift_amount":    str(amount),
        "deduction":      str(deduction),
        "taxable_base":   str(taxable),
        "tax":            str(tax),
        "effective_rate": str(eff_rate),
        "marginal_rate":  str(marginal_rate),
        "breakdown":      breakdown,
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
