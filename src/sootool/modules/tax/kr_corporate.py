"""Korean corporate income tax (법인세) calculator.

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


def _calc_minimum_tax(
    base:        Decimal,
    is_small:    bool,
    data:        dict[str, Any],
) -> Decimal:
    """Compute minimum tax floor (조특법 §132).

    Small firm: flat `small` rate.
    General firm: progressive brackets in `general_brackets`.
    """
    if is_small:
        rate = D(str(data["small"]))
        return base * rate

    # General: progressive brackets
    lower: Decimal = Decimal("0")
    total = Decimal("0")
    for bracket in data["general_brackets"]:
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))
        upper: Decimal | None = None if upper_raw is None else D(str(upper_raw))

        if upper is None:
            seg = base - lower if base > lower else Decimal("0")
            total += seg * rate
            break
        cap = min(base, upper)
        seg = cap - lower if cap > lower else Decimal("0")
        total += seg * rate
        lower = upper
        if base <= upper:
            break
    return total


@REGISTRY.tool(
    namespace="tax",
    name="kr_corporate",
    description=(
        "한국 법인세 계산 (법인세법 제55조). 누진 구간 + 최저한세. "
        "반환은 base_tax, minimum_tax, tax(=max), breakdown."
    ),
    version="1.0.0",
)
def tax_kr_corporate(
    taxable_income: str,
    year:           int,
    is_small:       bool = False,
    rounding:       str  = "HALF_UP",
    decimals:       int  = 0,
) -> dict[str, Any]:
    """Calculate Korean corporate income tax with minimum-tax floor.

    Args:
        taxable_income: 과세표준 (Decimal string, 원)
        year:           과세연도
        is_small:       중소기업 여부 (최저한세 적용 차등)
        rounding:       반올림 정책
        decimals:       소수점 자리수

    Returns:
        {base_tax, minimum_tax, tax, effective_rate, marginal_rate,
         breakdown, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_corporate",
        formula=(
            "base_tax = 누진세율 적용(taxable_income); "
            "minimum_tax = 과세표준 * 최저한세율; "
            "tax = max(base_tax, minimum_tax)"
        ),
    )

    policy_enum = _parse_rounding(rounding)
    income      = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_corporate", year)
    data       = policy_doc["data"]
    brackets   = data["brackets"]
    pv         = policy_doc["policy_version"]

    trace.input("taxable_income", taxable_income)
    trace.input("year",           year)
    trace.input("is_small",       is_small)
    trace.input("rounding",       rounding)
    trace.input("policy_version", pv)

    base_tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        income, brackets, policy_enum, decimals
    )

    min_tax_raw = _calc_minimum_tax(income, is_small, data["minimum_tax"])
    min_tax     = min_tax_raw.quantize(Decimal("1")) if decimals == 0 else min_tax_raw

    tax_final = max(base_tax, min_tax)

    trace.step("base_tax",     str(base_tax))
    trace.step("minimum_tax",  str(min_tax))
    trace.step("breakdown",    breakdown)
    trace.output(str(tax_final))

    resp = {
        "base_tax":       str(base_tax),
        "minimum_tax":    str(min_tax),
        "tax":            str(tax_final),
        "effective_rate": str(eff_rate),
        "marginal_rate":  str(marginal_rate),
        "breakdown":      breakdown,
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
