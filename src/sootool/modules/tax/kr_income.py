"""Korean income tax (종합소득세/근로소득세) calculator.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit       import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors      import InvalidInputError
from sootool.core.registry    import REGISTRY
from sootool.core.rounding    import RoundingPolicy
from sootool.modules.tax.progressive import (
    _calc_progressive,
    _parse_rounding,
)
from sootool.policies import load as policy_load


@REGISTRY.tool(
    namespace="tax",
    name="kr_income",
    description=(
        "한국 근로·종합소득세 계산. "
        "소득세법 누진세율 구간(정책 YAML)을 참조하여 세액 계산."
    ),
    version="1.0.0",
)
def tax_kr_income(
    taxable_income: str,
    year:           int,
    rounding:       str = "HALF_UP",
    decimals:       int = 0,
) -> dict[str, Any]:
    """Calculate Korean income tax using the official progressive brackets.

    Args:
        taxable_income: 과세표준 (Decimal string, 원)
        year:           과세연도
        rounding:       반올림 정책 (기본 HALF_UP)
        decimals:       소수점 자리수 (기본 0)

    Returns:
        {tax, effective_rate, marginal_rate, breakdown, policy_version, trace}

    Raises:
        UnsupportedPolicyError: 해당 연도 정책 파일이 없는 경우
    """
    trace = CalcTrace(
        tool="tax.kr_income",
        formula="소득세법 누진세율 구간별 세액 합산",
    )

    policy  = _parse_rounding(rounding)
    income  = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_income", year)
    brackets   = policy_doc["data"]["brackets"]
    pv         = policy_doc["policy_version"]

    trace.input("taxable_income",  taxable_income)
    trace.input("year",            year)
    trace.input("rounding",        rounding)
    trace.input("policy_version",  pv)

    tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        income, brackets, policy, decimals
    )

    trace.step("breakdown", breakdown)
    trace.output(str(tax))

    return {
        "tax":            str(tax),
        "effective_rate":  str(eff_rate),
        "marginal_rate":   str(marginal_rate),
        "breakdown":       breakdown,
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
