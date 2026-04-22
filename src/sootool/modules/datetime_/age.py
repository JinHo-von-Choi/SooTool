"""Age calculation (만나이) and date difference tools."""
from __future__ import annotations

from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise InvalidInputError(f"날짜 형식 오류: {s!r} (YYYY-MM-DD 필요)") from exc


@REGISTRY.tool(
    namespace="datetime",
    name="age",
    description="만나이 계산. 생일 이전/이후 경계 정확 처리.",
    version="1.0.0",
)
def age(
    birth_date: str,
    reference_date: str | None = None,
) -> dict[str, Any]:
    """Calculate Korean civil age (만나이) at reference_date.

    만나이: full years elapsed since birth_date. Increments on birthday.

    Args:
        birth_date:     생년월일 (YYYY-MM-DD)
        reference_date: 기준일 (YYYY-MM-DD). None이면 오늘(UTC).

    Returns:
        {years: int, months: int, days: int, trace}
    """
    trace = CalcTrace(
        tool="datetime.age",
        formula="age = relativedelta(reference_date, birth_date)",
    )
    birth = _parse_date(birth_date)
    ref   = _parse_date(reference_date) if reference_date else date.today()

    if ref < birth:
        raise InvalidInputError("reference_date는 birth_date 이후여야 합니다.")

    trace.input("birth_date",     birth_date)
    trace.input("reference_date", str(ref))

    delta = relativedelta(ref, birth)
    years  = delta.years
    months = delta.months
    days   = delta.days

    trace.step("years",  years)
    trace.step("months", months)
    trace.step("days",   days)
    trace.output({"years": years, "months": months, "days": days})

    return {
        "years":  years,
        "months": months,
        "days":   days,
        "trace":  trace.to_dict(),
    }


_UNIT_FACTORS = {
    "days":   1,
    "weeks":  7,
    "months": None,
    "years":  None,
}


@REGISTRY.tool(
    namespace="datetime",
    name="diff",
    description="두 날짜 간 기간 차이 계산. unit: days | weeks | months | years.",
    version="1.0.0",
)
def diff(
    start: str,
    end: str,
    unit: str,
) -> dict[str, Any]:
    """Calculate difference between two dates in the specified unit.

    Args:
        start: 시작일 (YYYY-MM-DD)
        end:   종료일 (YYYY-MM-DD)
        unit:  days | weeks | months | years

    Returns:
        {value: str (integer string), trace}
    """
    trace = CalcTrace(
        tool="datetime.diff",
        formula=f"diff = (end - start) in {unit}",
    )
    valid_units = {"days", "weeks", "months", "years"}
    if unit not in valid_units:
        raise InvalidInputError(f"지원하지 않는 unit: {unit!r}. 지원: {sorted(valid_units)}")

    start_d = _parse_date(start)
    end_d   = _parse_date(end)

    trace.input("start", start)
    trace.input("end",   end)
    trace.input("unit",  unit)

    if unit == "days":
        value = (end_d - start_d).days
    elif unit == "weeks":
        value = (end_d - start_d).days // 7
    elif unit == "months":
        delta = relativedelta(end_d, start_d)
        value = delta.years * 12 + delta.months
    elif unit == "years":
        delta = relativedelta(end_d, start_d)
        value = delta.years
    else:
        raise InvalidInputError(f"미지원 unit: {unit!r}")  # pragma: no cover

    trace.step("value", value)
    trace.output(value)

    return {
        "value": str(value),
        "trace": trace.to_dict(),
    }
