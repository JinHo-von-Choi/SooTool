"""Age calculation (만나이) and date difference tools."""
from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


class AgeResult(TracedResult):
    years:  int
    months: int
    days:   int


class DiffResult(TracedResult):
    value: str


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise InvalidInputError(f"날짜 형식 오류: {s!r} (YYYY-MM-DD 필요)") from exc


@REGISTRY.tool(
    namespace="datetime",
    name="age",
    description=(
        "만 나이(한국 법정 연령)를 years, months, days 정수로 계산한다. 날짜는 YYYY-MM-DD 이고 "
        "생일 당일에 한 살이 오른다. reference_date 를 생략하면 서버의 오늘 날짜를 쓰므로 실행일마다 "
        "결과가 달라진다. 기준일이 생일보다 앞서면 오류이며 세는나이는 계산하지 않는다."
    ),
    version="1.0.0",
)
def age(
    birth_date: str,
    reference_date: str | None = None,
) -> AgeResult:
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
    description=(
        "두 날짜의 차이를 unit(days | weeks | months | years) 단위의 정수 문자열 value 로 돌려준다. "
        "날짜는 YYYY-MM-DD 이다. weeks 는 일수를 7 로 나눈 몫(내림), months 와 years 는 가득 찬 달과 해만 "
        "세며 end 가 start 보다 앞서면 음수이다. 소수 단위나 남는 일수는 주지 않는다."
    ),
    version="1.0.0",
)
def diff(
    start: str,
    end: str,
    unit: str,
) -> DiffResult:
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
