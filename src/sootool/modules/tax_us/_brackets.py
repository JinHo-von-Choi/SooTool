"""tax_us 공통 구간 세액 계산.

Author: 최진호
Date: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.decimal_ops import D


def slice_tax(
    lo:       Decimal,
    hi:       Decimal,
    brackets: list[dict[str, Any]],
) -> tuple[Decimal, Decimal, list[dict[str, Any]]]:
    """구간표에서 소득 구간 (lo, hi] 에 해당하는 세액을 반올림 없이 계산한다.

    각 세율 구간(하한 초과, 상한 이하)과 (lo, hi] 의 겹치는 길이에 세율을 곱해 더한다.
    lo=0 이면 hi 전체에 대한 누진 세액이고, lo 를 일반소득으로 두면 그 위에 쌓인
    소득의 세액이다. 시간 복잡도 O(구간 수).

    Returns (tax, marginal_rate, breakdown). marginal_rate 는 겹침이 있는 가장 높은
    구간의 세율이며 겹침이 없으면 0 이다.
    """
    lower     = Decimal("0")
    total     = Decimal("0")
    marginal  = Decimal("0")
    breakdown = []

    for bracket in brackets:
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))
        upper     = None if upper_raw is None else D(str(upper_raw))

        seg_lo = lo if lo > lower else lower
        seg_hi = hi if upper is None or hi < upper else upper
        amount = seg_hi - seg_lo if seg_hi > seg_lo else Decimal("0")
        tax_in = amount * rate
        total += tax_in
        if amount > Decimal("0"):
            marginal = rate

        breakdown.append({
            "bracket":            {
                "lower": str(lower),
                "upper": str(upper) if upper is not None else "null",
                "rate":  str(rate),
            },
            "taxable_in_bracket": str(amount),
            "tax_in_bracket":     str(tax_in),
        })
        if upper is not None:
            lower = upper

    return total, marginal, breakdown


def schedule_tax(
    taxable:  Decimal,
    brackets: list[dict[str, Any]],
) -> Decimal:
    """세율 스케줄 세액을 반올림 없이 계산한다.

    모든 구간에 base(공시 표의 해당 구간 기준액)가 있으면 과세표준이 속한 구간의
    base + rate x (과세표준 - 하한) 으로 계산한다. 공시 표가 기준액을 정수로 끊어
    싣는 경우(NY 등) 표와 같은 값을 낸다. base 가 없으면 누진 합산 세액이다.
    """
    if not brackets or any("base" not in b for b in brackets):
        return slice_tax(Decimal("0"), taxable, brackets)[0]
    if taxable <= Decimal("0"):
        return Decimal("0")

    lower = Decimal("0")
    for bracket in brackets:
        upper_raw = bracket["upper"]
        if upper_raw is None or taxable <= D(str(upper_raw)):
            return D(str(bracket["base"])) + (taxable - lower) * D(str(bracket["rate"]))
        lower = D(str(upper_raw))
    return slice_tax(Decimal("0"), taxable, brackets)[0]
