"""Korean local income tax (지방소득세) calculator.

Author: 최진호
Date: 2026-04-24

지방세법 제92조: 지방소득세 = 소득세 * 10%.
고정 비율이므로 정책 YAML은 불요.
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply

_VALID_POLICIES = {p.value for p in RoundingPolicy}
_LOCAL_RATE = Decimal("0.10")


class TaxKrLocalIncomeTaxResult(TracedResult):
    income_tax:       str
    rate:             str
    local_income_tax: str


@REGISTRY.tool(
    namespace="tax",
    name="kr_local_income_tax",
    description=(
        "한국 개인 지방소득세를 소득세 본세의 10% 고정 비율로 계산한다(지방세법 제92조). "
        "income_tax 는 이미 산출된 소득세액(원, 0 이상 Decimal 문자열)이며 rounding 기본 DOWN, decimals 기본 0이라 원 미만을 버린다. "
        "과세표준이나 소득금액을 넣으면 안 되고 소득세 산출 후 그 세액을 넣어야 한다."
    ),
    version="1.0.0",
)
def tax_kr_local_income_tax(
    income_tax: str,
    rounding:   str = "DOWN",
    decimals:   int = 0,
) -> TaxKrLocalIncomeTaxResult:
    """Calculate Korean local income tax (지방소득세).

    Args:
        income_tax: 본세(소득세)액(원)
        rounding:   반올림 정책 (기본 DOWN: 원단위 절사)
        decimals:   소수점 자리수(기본 0)

    Returns:
        {income_tax, rate, local_income_tax, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_local_income_tax",
        formula="지방소득세 = 소득세 * 10%",
    )

    if rounding not in _VALID_POLICIES:
        raise InvalidInputError(
            f"rounding은 {sorted(_VALID_POLICIES)} 중 하나여야 합니다."
        )
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    base = D(income_tax)
    if base < Decimal("0"):
        raise InvalidInputError("income_tax는 0 이상이어야 합니다.")

    trace.input("income_tax", income_tax)
    trace.input("rounding",   rounding)
    trace.input("decimals",   decimals)

    raw  = base * _LOCAL_RATE
    tax  = round_apply(raw, decimals, RoundingPolicy(rounding))

    trace.step("raw_amount", str(raw))
    trace.output(str(tax))

    return {
        "income_tax":       str(base),
        "rate":             str(_LOCAL_RATE),
        "local_income_tax": str(tax),
        "trace":            trace.to_dict(),
    }
