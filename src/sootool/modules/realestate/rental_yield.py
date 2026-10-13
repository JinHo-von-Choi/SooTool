"""Rental yield calculator (임대수익률).

Author: 최진호
Date: 2026-04-22

수식:
  - Gross yield: annual_rent / property_price
  - Net yield:   (annual_rent - annual_expenses) / property_price
"""
from __future__ import annotations

from decimal import Context, Decimal, DecimalException, localcontext
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply


class RealestateRentalYieldResult(TracedResult):
    yield_pct: str


@REGISTRY.tool(
    namespace="realestate",
    name="rental_yield",
    description=(
        "임대수익률을 백분율(%) 문자열로 계산한다. gross 는 연간 임대수입 / 매입가격, net 은 (연간 임대수입 - "
        "연간 비용) / 매입가격이며 금액은 원 단위 문자열이다. rounding(기본 HALF_EVEN)으로 decimals(기본 2) "
        "자리까지 반올림하고, 비용이 임대수입보다 크면 net 은 음수다. gross 는 비용을 보지 않는다. "
        "오용 예: 월 임대료를 연 환산하지 않고 annual_rent 에 입력."
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
) -> RealestateRentalYieldResult:
    """Calculate rental yield with an isolated, input-sized Decimal context.

    Amounts must be finite; decimals must be a nonnegative integer.

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

    if any(not value.is_finite() for value in (rent, price, expenses)):
        raise InvalidInputError("금액은 유한한 숫자여야 합니다.")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
        raise InvalidInputError("decimals는 0 이상 정수여야 합니다.")

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

    # Preserve cancellation in net income and digits near rounding boundaries.
    amounts = [rent] if yield_type == "gross" else [rent, expenses]
    nonzero = [value for value in amounts if value != 0]
    highest_digit = max((value.adjusted() for value in nonzero), default=0)
    lowest_digit = min((int(value.as_tuple().exponent) for value in nonzero), default=0)
    integer_digits = max(1, highest_digit - price.adjusted() + 3)
    precision = max(
        50,
        highest_digit - lowest_digit + integer_digits
        + decimals + len(price.as_tuple().digits) + 10,
    )
    try:
        with localcontext(Context(prec=precision)):
            numerator = rent if yield_type == "gross" else rent - expenses
            raw_pct = numerator / price * D("100")
            yield_pct = round_apply(raw_pct, decimals, RoundingPolicy(rounding))
    except DecimalException as exc:
        raise InvalidInputError("입력값 또는 decimals가 Decimal 계산 범위를 벗어납니다.") from exc

    trace.step("numerator", str(numerator))
    trace.step("raw_pct",   str(raw_pct))
    trace.output(str(yield_pct))

    resp: dict[str, Any] = {
        "yield_pct": str(yield_pct),
        "trace":     trace.to_dict(),
    }
    return cast(RealestateRentalYieldResult, resp)
