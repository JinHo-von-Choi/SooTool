"""Korean income tax (종합소득세/근로소득세) calculator.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.modules.tax.progressive import (
    BracketBreakdown,
    _calc_progressive,
    _parse_rounding,
)
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class TaxKrIncomeResult(PolicyResult):
    tax:            str
    effective_rate: str
    marginal_rate:  str
    breakdown:      list[BracketBreakdown]


@REGISTRY.tool(
    namespace="tax",
    name="kr_income",
    description=(
        "한국 종합소득세·근로소득세 산출세액을 소득세법 제55조 기본세율(6~45% 누진, 정책 YAML)로 계산한다. "
        "taxable_income 은 공제를 모두 뺀 과세표준(원, Decimal 문자열)이고 year 는 필수다. "
        "구간별 세액과 실효·한계세율을 돌려주며 rounding(기본 HALF_UP)으로 decimals(기본 0)자리에 맞춘다. "
        "근로소득공제와 세액공제는 반영하지 않으므로 총급여를 그대로 넣으면 안 된다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_income(
    taxable_income: str,
    year:           int,
    rounding:       str = "HALF_UP",
    decimals:       int = 0,
) -> TaxKrIncomeResult:
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

    resp: dict[str, Any] = {
        "tax":            str(tax),
        "effective_rate":  str(eff_rate),
        "marginal_rate":   str(marginal_rate),
        "breakdown":       breakdown,
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
    return cast(TaxKrIncomeResult, enrich_response(resp, policy_doc))
