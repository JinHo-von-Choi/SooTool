"""Progressive bracket tax calculator.

Author: 최진호
Date: 2026-04-22
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


def _parse_rounding(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(
            f"유효하지 않은 rounding 정책: '{rounding}'. "
            f"허용값: {[p.value for p in RoundingPolicy]}"
        ) from exc


def _calc_progressive(
    taxable_income: Decimal,
    brackets:       list[dict[str, Any]],
    rounding:       RoundingPolicy,
    decimals:       int,
) -> tuple[Decimal, Decimal, Decimal, list[dict[str, Any]]]:
    """Core progressive bracket calculation.

    Returns (tax, effective_rate, marginal_rate, breakdown).
    Bracket boundary: lower-exclusive, upper-inclusive.
    """
    lower = Decimal("0")
    total_tax   = Decimal("0")
    marginal_rate = Decimal("0")
    breakdown     = []

    for i, bracket in enumerate(brackets):
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))

        upper: Decimal | None = None if upper_raw is None else D(str(upper_raw))

        if upper is not None and taxable_income <= lower:
            # income does not reach this bracket
            breakdown.append({
                "bracket":           {"lower": str(lower), "upper": str(upper), "rate": str(rate)},
                "taxable_in_bracket": "0",
                "tax_in_bracket":     "0",
            })
            lower = upper
            continue

        if upper is None:
            # top bracket: no upper limit
            taxable_in = taxable_income - lower if taxable_income > lower else Decimal("0")
            is_top     = True
        else:
            cap          = min(taxable_income, upper)
            taxable_in   = cap - lower if cap > lower else Decimal("0")
            is_top       = False

        tax_in    = taxable_in * rate
        total_tax += tax_in

        if taxable_in > Decimal("0"):
            marginal_rate = rate

        upper_str = str(upper) if upper is not None else "null"
        breakdown.append({
            "bracket":           {"lower": str(lower), "upper": upper_str, "rate": str(rate)},
            "taxable_in_bracket": str(taxable_in),
            "tax_in_bracket":     str(tax_in),
        })

        if upper is not None:
            lower = upper

        if not is_top and taxable_income <= (upper or Decimal("0")):
            # remaining brackets contribute 0
            for _j, rem_bracket in enumerate(brackets[i + 1:], i + 1):
                upper_r = rem_bracket["upper"]
                rate_r  = D(str(rem_bracket["rate"]))
                upper_r_d = None if upper_r is None else D(str(upper_r))
                upper_r_str = str(upper_r_d) if upper_r_d is not None else "null"
                breakdown.append({
                    "bracket":           {"lower": str(lower), "upper": upper_r_str, "rate": str(rate_r)},
                    "taxable_in_bracket": "0",
                    "tax_in_bracket":     "0",
                })
                if upper_r_d is not None:
                    lower = upper_r_d
            break

    rounded_tax = round_apply(total_tax, decimals, rounding)

    effective_rate = (
        round_apply(total_tax / taxable_income, 8, RoundingPolicy.HALF_UP)
        if taxable_income > Decimal("0") else Decimal("0")
    )

    return rounded_tax, effective_rate, marginal_rate, breakdown


def _validate_brackets(brackets: list[dict[str, Any]]) -> None:
    """Validate bracket list: ascending upper, last bracket has upper=null."""
    if not brackets:
        raise InvalidInputError("brackets는 하나 이상이어야 합니다.")

    prev_upper: Decimal | None = None
    for i, b in enumerate(brackets):
        if "rate" not in b:
            raise InvalidInputError(f"brackets[{i}]에 'rate' 필드가 없습니다.")
        upper_raw = b.get("upper")
        if upper_raw is None:
            if i != len(brackets) - 1:
                raise InvalidInputError(
                    f"upper=null은 마지막 구간에만 허용됩니다 (brackets[{i}])."
                )
        else:
            upper = D(str(upper_raw))
            if upper <= Decimal("0"):
                raise InvalidInputError(
                    f"brackets[{i}].upper는 0 초과여야 합니다."
                )
            if prev_upper is not None and upper <= prev_upper:
                raise InvalidInputError(
                    f"brackets는 upper 기준 오름차순이어야 합니다. "
                    f"brackets[{i}].upper={upper} <= 이전 upper={prev_upper}"
                )
            prev_upper = upper

    if brackets[-1].get("upper") is not None:
        raise InvalidInputError(
            "마지막 bracket의 upper는 null(무한대)이어야 합니다."
        )


@REGISTRY.tool(
    namespace="tax",
    name="progressive",
    description=(
        "일반 누진세율 구간 계산기. "
        "하한 초과 ~ 상한 이하 구간(lower-exclusive, upper-inclusive) 기준."
    ),
    version="1.0.0",
)
def tax_progressive(
    taxable_income: str,
    brackets:       list[dict[str, Any]],
    rounding:       str = "HALF_UP",
    decimals:       int = 0,
) -> dict[str, Any]:
    """Calculate tax using progressive (marginal) brackets.

    Args:
        taxable_income: 과세표준 (Decimal string)
        brackets: 세율 구간 목록. 각 항목은 {upper: str|null, rate: str}.
                  upper는 해당 구간의 상한(이하), null이면 최고 구간.
                  오름차순 정렬, 마지막 항목은 upper=null 필수.
        rounding: 반올림 정책 (기본 HALF_UP)
        decimals: 소수점 자리수 (기본 0)

    Returns:
        {tax, effective_rate, marginal_rate, breakdown, trace}
    """
    trace = CalcTrace(
        tool="tax.progressive",
        formula="각 구간별 (min(income,upper)-lower)*rate 합산",
    )

    policy  = _parse_rounding(rounding)
    income  = D(taxable_income)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")

    _validate_brackets(brackets)

    trace.input("taxable_income", taxable_income)
    trace.input("brackets",       brackets)
    trace.input("rounding",       rounding)
    trace.input("decimals",       decimals)

    tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        income, brackets, policy, decimals
    )

    trace.step("breakdown", breakdown)
    trace.output(str(tax))

    return {
        "tax":           str(tax),
        "effective_rate": str(eff_rate),
        "marginal_rate":  str(marginal_rate),
        "breakdown":      breakdown,
        "trace":          trace.to_dict(),
    }
