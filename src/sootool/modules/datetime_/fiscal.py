"""Fiscal year / quarter / payroll period utilities.

내부 자료형 (ADR-008):
- 날짜는 ISO 문자열 <-> datetime.date.
- 회계연도 정책은 국가별 고정 오프셋. YAML 외부화는 불필요 (법정 고정값).

지원:
- 회계연도 경계: 한국(KR), 미국(US), 일본(JP), 영국(UK).
- 분기 경계 (회계 분기): fiscal_year_start 기준.
- 세법 과세기간 판정: KR 양도소득세 기준 해당 연도 1/1~12/31.
- 월급 정산 주기: 월 단위 급여 기간 (payroll_period_of).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

# country -> fiscal year starting (month, day)
# KR/US: 회계연도 = 1/1
# JP:    회계연도 = 4/1 (학년도/회계연도 공통)
# UK:    회계연도(개인소득세) = 4/6
_FY_START: dict[str, tuple[int, int]] = {
    "KR": (1, 1),
    "US": (1, 1),
    "JP": (4, 1),
    "UK": (4, 6),
}


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise InvalidInputError(f"날짜 형식 오류: {s!r} (YYYY-MM-DD 필요)") from exc


def _fy_start_for(country: str, year: int) -> date:
    m, d = _FY_START[country]
    return date(year, m, d)


def _fiscal_year_of(d: date, country: str) -> int:
    """Return the fiscal-year label that contains the given date."""
    m, dd = _FY_START[country]
    boundary = date(d.year, m, dd)
    if d >= boundary:
        return d.year
    return d.year - 1


@REGISTRY.tool(
    namespace="datetime",
    name="fiscal_year",
    description=(
        "회계연도 경계 산정. country: KR | US | JP | UK. "
        "KR/US=1/1, JP=4/1, UK=4/6 기준."
    ),
    version="1.0.0",
)
def fiscal_year(as_of: str, country: str = "KR") -> dict[str, Any]:
    """Return the fiscal year bounds containing the given date.

    Args:
        as_of:   기준일 YYYY-MM-DD.
        country: KR | US | JP | UK.

    Returns:
        {fiscal_year, start_date, end_date, country, trace}
    """
    trace = CalcTrace(
        tool="datetime.fiscal_year",
        formula="start = FY_START[country] of max(year) ≤ as_of, end = start + 1y - 1d",
    )
    if country not in _FY_START:
        raise InvalidInputError(
            f"지원하지 않는 country: {country!r}. 지원: {sorted(_FY_START)}"
        )
    d = _parse_date(as_of)
    fy = _fiscal_year_of(d, country)
    start = _fy_start_for(country, fy)
    # end_date: day before next FY start
    next_start = _fy_start_for(country, fy + 1)
    end = next_start - timedelta(days=1)

    trace.input("as_of",   as_of)
    trace.input("country", country)
    trace.step("fy_label", fy)
    trace.step("start",    start.isoformat())
    trace.step("end",      end.isoformat())
    trace.output({"fiscal_year": fy})

    return {
        "fiscal_year":  fy,
        "start_date":   start.isoformat(),
        "end_date":     end.isoformat(),
        "country":      country,
        "trace":        trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="datetime",
    name="fiscal_quarter",
    description=(
        "회계분기 경계 산정. country의 회계연도 시작일 기준 Q1..Q4를 3개월 단위로 계산."
    ),
    version="1.0.0",
)
def fiscal_quarter(as_of: str, country: str = "KR") -> dict[str, Any]:
    """Return the fiscal quarter containing the given date."""
    trace = CalcTrace(
        tool="datetime.fiscal_quarter",
        formula="Qn 시작 = FY_start + 3*(n-1)개월, 종료 = 다음 Q 시작 - 1일",
    )
    if country not in _FY_START:
        raise InvalidInputError(
            f"지원하지 않는 country: {country!r}. 지원: {sorted(_FY_START)}"
        )
    d = _parse_date(as_of)
    fy = _fiscal_year_of(d, country)
    fy_start = _fy_start_for(country, fy)

    # Quarter boundaries: FY_start, +3m, +6m, +9m, +12m
    q_starts: list[date] = []
    for k in range(5):
        month = ((fy_start.month - 1 + 3 * k) % 12) + 1
        year  = fy_start.year + ((fy_start.month - 1 + 3 * k) // 12)
        try:
            q_starts.append(date(year, month, fy_start.day))
        except ValueError:
            # fallback for day > 28 (e.g. FY_start=4/6, all quarters use day=6)
            q_starts.append(date(year, month, min(fy_start.day, 28)))

    quarter = 0
    for i in range(4):
        if q_starts[i] <= d < q_starts[i + 1]:
            quarter = i + 1
            break

    if quarter == 0:
        raise DomainConstraintError(
            f"분기 계산 실패: as_of={as_of}, fy={fy}"
        )

    start = q_starts[quarter - 1]
    end   = q_starts[quarter] - timedelta(days=1)

    trace.input("as_of",   as_of)
    trace.input("country", country)
    trace.step("fiscal_year", fy)
    trace.step("quarter",     quarter)
    trace.step("start",       start.isoformat())
    trace.step("end",         end.isoformat())
    trace.output({"quarter": quarter, "fiscal_year": fy})

    return {
        "fiscal_year":  fy,
        "quarter":      quarter,
        "start_date":   start.isoformat(),
        "end_date":     end.isoformat(),
        "country":      country,
        "trace":        trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="datetime",
    name="tax_period_kr",
    description=(
        "한국 세법 상 과세기간 판정 (소득세 기준 1/1~12/31). "
        "주어진 날짜가 속한 과세기간의 경계와 라벨을 반환."
    ),
    version="1.0.0",
)
def tax_period_kr(as_of: str) -> dict[str, Any]:
    """Return Korean tax period (calendar year) containing the given date."""
    trace = CalcTrace(
        tool="datetime.tax_period_kr",
        formula="과세기간 = [YYYY-01-01, YYYY-12-31], 소득세법 제5조",
    )
    d = _parse_date(as_of)
    start = date(d.year, 1, 1)
    end   = date(d.year, 12, 31)

    trace.input("as_of", as_of)
    trace.step("tax_year", d.year)
    trace.step("start",    start.isoformat())
    trace.step("end",      end.isoformat())
    trace.output({"tax_year": d.year})

    return {
        "tax_year":    d.year,
        "start_date":  start.isoformat(),
        "end_date":    end.isoformat(),
        "country":     "KR",
        "trace":       trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="datetime",
    name="payroll_period",
    description=(
        "월급 정산 주기 산출. start_day 기준 월별 급여 기간을 계산한다 (기본 매월 1일 시작)."
    ),
    version="1.0.0",
)
def payroll_period(as_of: str, start_day: int = 1) -> dict[str, Any]:
    """Return the payroll period containing the given date.

    Args:
        as_of:     기준일 YYYY-MM-DD.
        start_day: 급여 기간 시작일 (1~28), 기본 1.

    Returns:
        {period_start, period_end, trace}
    """
    trace = CalcTrace(
        tool="datetime.payroll_period",
        formula="월급 기간 = [YYYY-MM-start_day, 다음달 start_day - 1]",
    )
    if not 1 <= start_day <= 28:
        raise InvalidInputError(
            f"start_day는 1-28 범위여야 합니다: {start_day}"
        )
    d = _parse_date(as_of)
    trace.input("as_of",     as_of)
    trace.input("start_day", start_day)

    if d.day >= start_day:
        period_start = date(d.year, d.month, start_day)
    else:
        # previous month
        if d.month == 1:
            period_start = date(d.year - 1, 12, start_day)
        else:
            period_start = date(d.year, d.month - 1, start_day)

    # period_end = next month's start_day - 1
    if period_start.month == 12:
        next_start = date(period_start.year + 1, 1, start_day)
    else:
        next_start = date(period_start.year, period_start.month + 1, start_day)
    period_end = next_start - timedelta(days=1)

    trace.step("period_start", period_start.isoformat())
    trace.step("period_end",   period_end.isoformat())
    trace.output({
        "period_start": period_start.isoformat(),
        "period_end":   period_end.isoformat(),
    })

    return {
        "period_start": period_start.isoformat(),
        "period_end":   period_end.isoformat(),
        "trace":        trace.to_dict(),
    }
