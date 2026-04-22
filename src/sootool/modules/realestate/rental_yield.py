"""Rental yield calculator (임대수익률).

Author: 최진호
Date: 2026-04-22

수식:
  - Gross yield: annual_rent / property_price
  - Net yield:   (annual_rent - annual_expenses) / property_price
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


@REGISTRY.tool(
    namespace="realestate",
    name="rental_yield",
    description=(
        "임대수익률 계산. "
        "gross: annual_rent / property_price. "
        "net: (annual_rent - annual_expenses) / property_price. "
        "결과: 백분율(%)."
    ),
    version="1.0.0",
)
def realestate_rental_yield(
    annual_rent:     str,
    property_price:  str,
    annual_expenses: str       = "0",
    yield_type:      str       = "gross",
    rounding:        str       = "HALF_EVEN",
    decimals:        int       = 2,
) -> dict[str, Any]:
    """Calculate rental yield.

    Args:
        annual_rent:     연간 임대 수입 (원, Decimal string)
        property_price:  매입 가격 (원, Decimal string)
        annual_expenses: 연간 비용 (원, Decimal string, 기본 0)
        yield_type:      수익률 유형 ("gross" | "net")
        rounding:        반올림 정책 (기본 "HALF_EVEN")
        decimals:        소수점 자리수 (기본 2)

    Returns:
        {yield_pct: str (%), trace}
    """
    trace = CalcTrace(
        tool="realestate.rental_yield",
        formula=(
            "gross: annual_rent / property_price * 100; "
            "net: (annual_rent - annual_expenses) / property_price * 100"
        ),
    )

    valid_types = {"gross", "net"}
    if yield_type not in valid_types:
        raise InvalidInputError(f"yield_type은 {valid_types} 중 하나여야 합니다.")

    valid_roundings = {"HALF_EVEN", "HALF_UP", "DOWN", "UP", "FLOOR", "CEIL"}
    if rounding not in valid_roundings:
        raise InvalidInputError(f"rounding은 {valid_roundings} 중 하나여야 합니다.")

    rent     = D(annual_rent)
    price    = D(property_price)
    expenses = D(annual_expenses)

    if rent < Decimal("0"):
        raise InvalidInputError("annual_rent는 0 이상이어야 합니다.")
    if price <= Decimal("0"):
        raise InvalidInputError("property_price는 0보다 커야 합니다.")
    if expenses < Decimal("0"):
        raise InvalidInputError("annual_expenses는 0 이상이어야 합니다.")

    trace.input("annual_rent",     annual_rent)
    trace.input("property_price",  property_price)
    trace.input("annual_expenses", annual_expenses)
    trace.input("yield_type",      yield_type)

    if yield_type == "gross":
        numerator = rent
    else:
        numerator = rent - expenses

    raw_ratio = numerator / price
    raw_pct   = raw_ratio * D("100")

    rounding_policy = RoundingPolicy(rounding)
    yield_pct = round_apply(raw_pct, decimals, rounding_policy)

    trace.step("numerator", str(numerator))
    trace.step("raw_pct",   str(raw_pct))
    trace.output(str(yield_pct))

    return {
        "yield_pct": str(yield_pct),
        "trace":     trace.to_dict(),
    }
