"""Korean rural special tax (농어촌특별세) calculator.

Author: 최진호
Date: 2026-04-24

농어촌특별세법 제5조:
  - 본세 부가분: 본세 * 10%
  - 감면세액 부가분: 감면액 * 20%
도구는 두 경로를 선택 가능.
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
_BASE_RATE      = Decimal("0.10")
_REDUCED_RATE   = Decimal("0.20")
_VALID_MODES    = {"base", "reduced"}


class TaxKrRuralSpecialTaxResult(TracedResult):
    amount:            str
    mode:              str
    rate:              str
    rural_special_tax: str


@REGISTRY.tool(
    namespace="tax",
    name="kr_rural_special_tax",
    description=(
        "한국 농어촌특별세를 계산한다(농어촌특별세법 제5조). mode=base 는 본세액 x 10%, mode=reduced 는 감면세액 x 20%이고 "
        "amount 는 해당 금액(원, 0 이상 Decimal 문자열)이다. rounding 기본 DOWN, decimals 기본 0이라 원 미만을 버린다. "
        "과세표준이 아니라 본세 또는 감면액을 넣어야 하며 mode 를 바꾸면 세율이 달라진다."
    ),
    version="1.0.0",
)
def tax_kr_rural_special_tax(
    amount:   str,
    mode:     str = "base",
    rounding: str = "DOWN",
    decimals: int = 0,
) -> TaxKrRuralSpecialTaxResult:
    """Calculate Korean rural special tax (농어촌특별세).

    Args:
        amount:   본세액(mode="base") 또는 감면액(mode="reduced"), 원
        mode:     "base" → 본세*10%, "reduced" → 감면액*20%
        rounding: 반올림 정책 (기본 DOWN)
        decimals: 소수점 자리수(기본 0)

    Returns:
        {amount, mode, rate, rural_special_tax, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_rural_special_tax",
        formula="base: 본세 * 10%; reduced: 감면액 * 20%",
    )

    if mode not in _VALID_MODES:
        raise InvalidInputError(
            f"mode는 {sorted(_VALID_MODES)} 중 하나여야 합니다."
        )
    if rounding not in _VALID_POLICIES:
        raise InvalidInputError(
            f"rounding은 {sorted(_VALID_POLICIES)} 중 하나여야 합니다."
        )
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    base = D(amount)
    if base < Decimal("0"):
        raise InvalidInputError("amount는 0 이상이어야 합니다.")

    rate = _BASE_RATE if mode == "base" else _REDUCED_RATE

    trace.input("amount",   amount)
    trace.input("mode",     mode)
    trace.input("rounding", rounding)
    trace.input("decimals", decimals)

    raw = base * rate
    tax = round_apply(raw, decimals, RoundingPolicy(rounding))

    trace.step("raw_amount", str(raw))
    trace.output(str(tax))

    return {
        "amount":            str(base),
        "mode":              mode,
        "rate":              str(rate),
        "rural_special_tax": str(tax),
        "trace":             trace.to_dict(),
    }
