"""Business days tools: add_business_days and count_business_days."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import holidays

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise InvalidInputError(f"날짜 형식 오류: {s!r} (YYYY-MM-DD 필요)") from exc


def _is_business_day(d: date, holiday_set: set[date]) -> bool:
    return d.weekday() < 5 and d not in holiday_set


def _build_holiday_set(country: str, years: set[int], extra_holidays: list[str]) -> set[date]:
    try:
        hols = holidays.country_holidays(country, years=list(years))
    except Exception as exc:
        raise InvalidInputError(f"지원하지 않는 국가 코드: {country!r} ({exc})") from exc
    holiday_set: set[date] = set(hols.keys())
    for ds in extra_holidays:
        holiday_set.add(_parse_date(ds))
    return holiday_set


@REGISTRY.tool(
    namespace="datetime",
    name="add_business_days",
    description="영업일 기준으로 start_date에 days를 더한 날짜를 반환. 주말·공휴일 자동 제외.",
    version="1.0.0",
)
def add_business_days(
    start_date: str,
    days: int,
    country: str = "KR",
    extra_holidays: list[str] | None = None,
) -> dict[str, Any]:
    """Add business days to a start date, skipping weekends and holidays.

    Args:
        start_date:      시작일 (YYYY-MM-DD)
        days:            더할 영업일 수
        country:         국가 코드 (holidays 패키지 코드, 기본 KR)
        extra_holidays:  추가 휴일 리스트 (YYYY-MM-DD 문자열)

    Returns:
        {end_date, trace}
    """
    trace = CalcTrace(
        tool="datetime.add_business_days",
        formula="end_date = start_date + days (business days, skipping weekends + holidays)",
    )
    if extra_holidays is None:
        extra_holidays = []

    start = _parse_date(start_date)
    trace.input("start_date",     start_date)
    trace.input("days",           days)
    trace.input("country",        country)
    trace.input("extra_holidays", extra_holidays)

    if days == 0:
        trace.output(start_date)
        return {"end_date": start_date, "trace": trace.to_dict()}

    # Determine year range to cover (add buffer for long spans)
    end_estimate_year = start.year + (abs(days) // 200 + 2)
    years = set(range(start.year, end_estimate_year + 1))
    holiday_set = _build_holiday_set(country, years, extra_holidays)

    current = start
    step    = 1 if days > 0 else -1
    remaining = abs(days)

    while remaining > 0:
        current = current + timedelta(days=step)
        if _is_business_day(current, holiday_set):
            remaining -= 1

    end_date_str = current.isoformat()
    trace.step("holiday_count", len(holiday_set))
    trace.output(end_date_str)

    return {"end_date": end_date_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="datetime",
    name="count_business_days",
    description="start~end 사이 영업일 수 계산 (양 끝 날짜 포함).",
    version="1.0.0",
)
def count_business_days(
    start: str,
    end: str,
    country: str = "KR",
) -> dict[str, Any]:
    """Count business days between start and end dates (inclusive).

    Args:
        start:   시작일 (YYYY-MM-DD)
        end:     종료일 (YYYY-MM-DD)
        country: 국가 코드

    Returns:
        {count, trace}
    """
    trace = CalcTrace(
        tool="datetime.count_business_days",
        formula="count = sum(1 for d in [start..end] if is_business_day(d))",
    )
    start_d = _parse_date(start)
    end_d   = _parse_date(end)

    if end_d < start_d:
        raise InvalidInputError("end는 start 이후여야 합니다.")

    trace.input("start",   start)
    trace.input("end",     end)
    trace.input("country", country)

    years = set(range(start_d.year, end_d.year + 1))
    holiday_set = _build_holiday_set(country, years, [])

    count   = 0
    current = start_d
    while current <= end_d:
        if _is_business_day(current, holiday_set):
            count += 1
        current += timedelta(days=1)

    trace.step("total_calendar_days", (end_d - start_d).days + 1)
    trace.output(count)

    return {"count": count, "trace": trace.to_dict()}
