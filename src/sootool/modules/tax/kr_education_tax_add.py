"""Korean local education tax surcharge (지방교육세) calculator.

Author: 최진호
Date: 2026-04-24

지방세법 제151조: 지방교육세는 본세(재산세·취득세·등록면허세·자동차세·담배소비세 등)에
부가되는 목적세로, 본세에 20%를 과세. 본 도구는 본세*0.20 을 계산한다.
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

_VALID_POLICIES = {p.value for p in RoundingPolicy}
_DEFAULT_RATE = Decimal("0.20")


@REGISTRY.tool(
    namespace="tax",
    name="kr_education_tax_add",
    description=(
        "한국 지방교육세 부가 계산 (지방세법 제151조). "
        "재산세·취득세·등록면허세 등 본세의 20%."
    ),
    version="1.0.0",
)
def tax_kr_education_tax_add(
    base_tax: str,
    rate:     str = "0.20",
    rounding: str = "DOWN",
    decimals: int = 0,
) -> dict[str, Any]:
    """Calculate Korean local education tax surcharge.

    Args:
        base_tax: 본세액(재산세·취득세·등록면허세 등, 원)
        rate:     부가세율 (기본 0.20, 본세에 따라 차등 가능)
        rounding: 반올림 정책 (기본 DOWN)
        decimals: 소수점 자리수(기본 0)

    Returns:
        {base_tax, rate, education_tax, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_education_tax_add",
        formula="지방교육세 = 본세 * rate (기본 20%)",
    )

    if rounding not in _VALID_POLICIES:
        raise InvalidInputError(
            f"rounding은 {sorted(_VALID_POLICIES)} 중 하나여야 합니다."
        )
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    base      = D(base_tax)
    rate_dec  = D(rate) if rate != "0.20" else _DEFAULT_RATE

    if base < Decimal("0"):
        raise InvalidInputError("base_tax는 0 이상이어야 합니다.")
    if rate_dec < Decimal("0"):
        raise InvalidInputError("rate는 0 이상이어야 합니다.")
    if rate_dec > Decimal("1"):
        raise InvalidInputError("rate는 1 이하여야 합니다.")

    trace.input("base_tax", base_tax)
    trace.input("rate",     rate)
    trace.input("rounding", rounding)
    trace.input("decimals", decimals)

    raw  = base * rate_dec
    tax  = round_apply(raw, decimals, RoundingPolicy(rounding))

    trace.step("raw_amount", str(raw))
    trace.output(str(tax))

    return {
        "base_tax":      str(base),
        "rate":          str(rate_dec),
        "education_tax": str(tax),
        "trace":         trace.to_dict(),
    }
