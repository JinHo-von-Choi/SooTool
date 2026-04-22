"""Day count conventions for interest calculation."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_CONVENTIONS = frozenset(["30/360", "ACT/365", "ACT/ACT", "ACT/360"])


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise InvalidInputError(f"날짜 형식 오류: {s!r} (YYYY-MM-DD 필요)") from exc


def _act_days(start: date, end: date) -> int:
    return (end - start).days


def _30_360_days(start: date, end: date) -> int:
    """30/360 day count (Bond Basis / ISDA 30/360).

    Formula: 360*(Y2-Y1) + 30*(M2-M1) + (D2-D1)
    where D1=min(D1,30), D2=min(D2,30) if D1=30.
    """
    y1, m1, d1 = start.year, start.month, start.day
    y2, m2, d2 = end.year,   end.month,   end.day
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 == 30:
        d2 = 30
    return 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)


def _is_leap(year: int) -> bool:
    return calendar.isleap(year)


def _act_act_year_fraction(start: date, end: date) -> Decimal:
    """ACT/ACT (ISDA): actual days / days in the year containing start."""
    if start == end:
        return Decimal("0")
    if start.year == end.year:
        days_in_year = 366 if _is_leap(start.year) else 365
        return div(D(str((end - start).days)), D(str(days_in_year)))
    # Multi-year: split at year boundaries
    total = Decimal("0")
    current = start
    while current.year < end.year:
        year_end = date(current.year + 1, 1, 1)
        days_in_year = 366 if _is_leap(current.year) else 365
        portion = (year_end - current).days
        total += div(D(str(portion)), D(str(days_in_year)))
        current = year_end
    # Remaining portion in last year
    if current < end:
        days_in_year = 366 if _is_leap(current.year) else 365
        portion = (end - current).days
        total += div(D(str(portion)), D(str(days_in_year)))
    return total


@REGISTRY.tool(
    namespace="datetime",
    name="day_count",
    description="이자 일수 계산. 컨벤션: 30/360 | ACT/365 | ACT/ACT | ACT/360",
    version="1.0.0",
)
def day_count(
    start: str,
    end: str,
    convention: str,
) -> dict[str, Any]:
    """Calculate day count and year fraction for interest calculations.

    Args:
        start:      시작일 (YYYY-MM-DD)
        end:        종료일 (YYYY-MM-DD)
        convention: 30/360 | ACT/365 | ACT/ACT | ACT/360

    Returns:
        {days: int, year_fraction: str (Decimal string), trace}
    """
    trace = CalcTrace(
        tool="datetime.day_count",
        formula=f"days & year_fraction using {convention} convention",
    )
    if convention not in _CONVENTIONS:
        raise InvalidInputError(
            f"지원하지 않는 컨벤션: {convention!r}. 지원: {sorted(_CONVENTIONS)}"
        )

    start_d = _parse_date(start)
    end_d   = _parse_date(end)

    if end_d < start_d:
        raise InvalidInputError("end는 start 이후여야 합니다.")

    trace.input("start",      start)
    trace.input("end",        end)
    trace.input("convention", convention)

    if convention == "30/360":
        days          = _30_360_days(start_d, end_d)
        year_fraction = div(D(str(days)), D("360"))

    elif convention == "ACT/365":
        days          = _act_days(start_d, end_d)
        year_fraction = div(D(str(days)), D("365"))

    elif convention == "ACT/ACT":
        days          = _act_days(start_d, end_d)
        year_fraction = _act_act_year_fraction(start_d, end_d)

    elif convention == "ACT/360":
        days          = _act_days(start_d, end_d)
        year_fraction = div(D(str(days)), D("360"))

    else:
        raise InvalidInputError(f"미지원 컨벤션: {convention!r}")  # pragma: no cover

    trace.step("days",          days)
    trace.step("year_fraction", str(year_fraction))
    trace.output({"days": days, "year_fraction": str(year_fraction)})

    return {
        "days":          days,
        "year_fraction": str(year_fraction),
        "trace":         trace.to_dict(),
    }
