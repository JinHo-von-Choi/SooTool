"""Accounting depreciation tools: straight-line, declining balance, units-of-production."""
from __future__ import annotations

from decimal import Decimal
from typing import TypedDict

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul, sub
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy, apply


class StraightLineRow(TypedDict):
    year:           int
    depreciation:   str
    book_value_end: str


class DecliningBalanceRow(TypedDict):
    year:             int
    book_value_start: str
    depreciation:     str
    book_value_end:   str


class UnitsOfProductionRow(TypedDict):
    period:         int
    units:          int
    depreciation:   str
    book_value_end: str


class DepreciationStraightLineResult(TracedResult):
    annual_expense: str
    schedule:       list[StraightLineRow]


class DepreciationDecliningBalanceResult(TracedResult):
    schedule: list[DecliningBalanceRow]


class DepreciationUnitsOfProductionResult(TracedResult):
    schedule: list[UnitsOfProductionRow]


def _parse_policy(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(f"유효하지 않은 반올림 정책: {rounding!r}") from exc


@REGISTRY.tool(
    namespace="accounting",
    name="depreciation_straight_line",
    description=(
        "정액법 감가상각 스케줄을 계산한다. 연 감가비 = (취득원가 - 잔존가치) / 내용연수(life_years, 1 이상 정수), "
        "금액은 Decimal 문자열. decimals(기본 0)자리로 rounding(기본 HALF_EVEN) 처리하고 마지막 해는 장부가가 잔존가치에 "
        "맞도록 잔액을 상각한다. 월할이나 기중 취득 안분은 지원하지 않는다."
    ),
    version="1.0.0",
)
def depreciation_straight_line(
    cost: str,
    salvage: str,
    life_years: int,
    decimals: int = 0,
    rounding: str = "HALF_EVEN",
) -> DepreciationStraightLineResult:
    """Straight-line depreciation schedule.

    Formula: annual_expense = (cost - salvage) / life_years

    Args:
        cost:       취득원가 (Decimal string)
        salvage:    잔존가치 (Decimal string)
        life_years: 내용연수
        decimals:   반올림 소수점 자릿수
        rounding:   반올림 정책 (HALF_EVEN, HALF_UP, DOWN, UP, ...)

    Returns:
        {annual_expense, schedule[{year, depreciation, book_value_end}], trace}
    """
    trace = CalcTrace(
        tool="accounting.depreciation_straight_line",
        formula="annual = (cost - salvage) / life_years",
    )
    policy = _parse_policy(rounding)

    cost_d    = D(cost)
    salvage_d = D(salvage)

    if life_years <= 0:
        raise InvalidInputError("life_years는 1 이상이어야 합니다.")
    if cost_d < salvage_d:
        raise InvalidInputError("cost는 salvage 이상이어야 합니다.")

    trace.input("cost",       cost)
    trace.input("salvage",    salvage)
    trace.input("life_years", life_years)
    trace.input("decimals",   decimals)
    trace.input("rounding",   rounding)

    depreciable = sub(cost_d, salvage_d)
    annual_raw  = div(depreciable, D(str(life_years)))
    annual      = apply(annual_raw, decimals, policy)

    trace.step("depreciable_base", str(depreciable))
    trace.step("annual_raw",       str(annual_raw))
    trace.step("annual_expense",   str(annual))

    schedule: list[StraightLineRow] = []
    book_value = cost_d
    for year in range(1, life_years + 1):
        remaining = sub(book_value, salvage_d)
        if year < life_years:
            dep = apply(annual_raw, decimals, policy)
        else:
            # Last year: depreciate exactly to salvage to avoid float drift
            dep = apply(remaining, decimals, policy)
        book_value = sub(book_value, dep)
        schedule.append({
            "year":           year,
            "depreciation":   str(dep),
            "book_value_end": str(book_value),
        })

    trace.output({"annual_expense": str(annual), "schedule_rows": len(schedule)})

    return {
        "annual_expense": str(annual),
        "schedule":       schedule,
        "trace":          trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="accounting",
    name="depreciation_declining_balance",
    description=(
        "정률법 감가상각 스케줄을 계산한다. 연도별 감가비 = 기초 장부가 x 감가율(rate, 0 초과 1 미만 Decimal 문자열)이며 "
        "장부가는 잔존가치 아래로 내려가지 않고 도달하면 이후 연도 감가비는 0 이다. decimals(기본 0)자리로 "
        "rounding(기본 HALF_EVEN) 처리한다. 감가율은 입력값 그대로 쓰며 내용연수로 역산하지 않는다."
    ),
    version="1.0.0",
)
def depreciation_declining_balance(
    cost: str,
    salvage: str,
    rate: str,
    life_years: int,
    decimals: int = 0,
    rounding: str = "HALF_EVEN",
) -> DepreciationDecliningBalanceResult:
    """Declining balance depreciation schedule.

    Formula: dep_year = book_value_beginning * rate
    Constraint: book_value never falls below salvage.

    Args:
        cost:       취득원가 (Decimal string)
        salvage:    잔존가치 (Decimal string)
        rate:       감가율 e.g. "0.25"
        life_years: 내용연수
        decimals:   반올림 소수점 자릿수
        rounding:   반올림 정책

    Returns:
        {schedule[{year, book_value_start, depreciation, book_value_end}], trace}
    """
    trace = CalcTrace(
        tool="accounting.depreciation_declining_balance",
        formula="dep = book_value_start * rate; book_value = max(book_value - dep, salvage)",
    )
    policy = _parse_policy(rounding)

    cost_d    = D(cost)
    salvage_d = D(salvage)
    rate_d    = D(rate)

    if life_years <= 0:
        raise InvalidInputError("life_years는 1 이상이어야 합니다.")
    if rate_d <= Decimal("0") or rate_d >= Decimal("1"):
        raise InvalidInputError("rate는 (0, 1) 범위여야 합니다.")
    if cost_d < salvage_d:
        raise InvalidInputError("cost는 salvage 이상이어야 합니다.")

    trace.input("cost",       cost)
    trace.input("salvage",    salvage)
    trace.input("rate",       rate)
    trace.input("life_years", life_years)
    trace.input("decimals",   decimals)
    trace.input("rounding",   rounding)

    schedule: list[DecliningBalanceRow] = []
    book_value = cost_d

    for year in range(1, life_years + 1):
        bv_start = book_value
        dep_raw  = mul(bv_start, rate_d)
        dep      = apply(dep_raw, decimals, policy)

        # Do not depreciate below salvage
        if sub(book_value, dep) < salvage_d:
            dep = apply(sub(book_value, salvage_d), decimals, policy)

        book_value = sub(book_value, dep)
        # Clamp to salvage in case of rounding edge cases
        if book_value < salvage_d:
            book_value = salvage_d

        schedule.append({
            "year":             year,
            "book_value_start": str(bv_start),
            "depreciation":     str(dep),
            "book_value_end":   str(book_value),
        })

        # Once at salvage, no more depreciation
        if book_value <= salvage_d:
            for remaining_year in range(year + 1, life_years + 1):
                schedule.append({
                    "year":             remaining_year,
                    "book_value_start": str(salvage_d),
                    "depreciation":     "0",
                    "book_value_end":   str(apply(salvage_d, decimals, policy)),
                })
            break

    trace.output({"schedule_rows": len(schedule)})

    return {
        "schedule": schedule,
        "trace":    trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="accounting",
    name="depreciation_units_of_production",
    description=(
        "생산량비례법 감가상각 스케줄을 계산한다. 기간 감가비 = (취득원가 - 잔존가치) / 총생산량 x 기간 생산량. "
        "total_units 는 1 이상 정수, period_units 는 기간별 생산량 정수 목록이며 금액은 Decimal 문자열. decimals(기본 0)자리로 "
        "rounding(기본 HALF_EVEN) 처리한다. 누적 생산량이 총생산량을 넘어도 오류 없이 장부가가 잔존가치에서 멈춘다."
    ),
    version="1.0.0",
)
def depreciation_units_of_production(
    cost: str,
    salvage: str,
    total_units: int,
    period_units: list[int],
    decimals: int = 0,
    rounding: str = "HALF_EVEN",
) -> DepreciationUnitsOfProductionResult:
    """Units-of-production depreciation schedule.

    Formula: dep_period = (cost - salvage) / total_units * period_units

    Args:
        cost:         취득원가 (Decimal string)
        salvage:      잔존가치 (Decimal string)
        total_units:  예상 총 생산량
        period_units: 기간별 실제 생산량 리스트
        decimals:     반올림 소수점 자릿수
        rounding:     반올림 정책

    Returns:
        {schedule[{period, units, depreciation, book_value_end}], trace}
    """
    trace = CalcTrace(
        tool="accounting.depreciation_units_of_production",
        formula="dep = (cost - salvage) / total_units * period_units",
    )
    policy = _parse_policy(rounding)

    cost_d    = D(cost)
    salvage_d = D(salvage)

    if total_units <= 0:
        raise InvalidInputError("total_units는 1 이상이어야 합니다.")
    if cost_d < salvage_d:
        raise InvalidInputError("cost는 salvage 이상이어야 합니다.")

    trace.input("cost",         cost)
    trace.input("salvage",      salvage)
    trace.input("total_units",  total_units)
    trace.input("period_units", period_units)
    trace.input("decimals",     decimals)
    trace.input("rounding",     rounding)

    depreciable  = sub(cost_d, salvage_d)
    rate_per_unit = div(depreciable, D(str(total_units)))

    trace.step("depreciable_base", str(depreciable))
    trace.step("rate_per_unit",    str(rate_per_unit))

    schedule: list[UnitsOfProductionRow] = []
    book_value = cost_d

    for i, units in enumerate(period_units):
        period   = i + 1
        dep_raw  = mul(rate_per_unit, D(str(units)))
        dep      = apply(dep_raw, decimals, policy)
        # Never depreciate below salvage
        if sub(book_value, dep) < salvage_d:
            dep = apply(sub(book_value, salvage_d), decimals, policy)
        book_value = sub(book_value, dep)
        schedule.append({
            "period":         period,
            "units":          units,
            "depreciation":   str(dep),
            "book_value_end": str(book_value),
        })

    trace.output({"schedule_rows": len(schedule)})

    return {
        "schedule": schedule,
        "trace":    trace.to_dict(),
    }
