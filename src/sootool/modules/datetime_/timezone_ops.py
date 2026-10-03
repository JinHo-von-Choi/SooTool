"""Timezone conversion tool using stdlib zoneinfo."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


class TzConvertResult(TracedResult):
    iso_datetime: str


def _resolve_tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError) as exc:
        raise InvalidInputError(f"알 수 없는 IANA 타임존: {tz_name!r}") from exc


def _parse_iso(iso_datetime: str, from_tz: ZoneInfo) -> datetime:
    """Parse ISO 8601 datetime. If naive, attach from_tz. If aware, validate/replace."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(iso_datetime, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=from_tz)
            return dt
        except ValueError:
            continue
    raise InvalidInputError(f"ISO 8601 형식 파싱 실패: {iso_datetime!r}")


@REGISTRY.tool(
    namespace="datetime",
    name="tz_convert",
    description=(
        "IANA 타임존 사이에서 시각을 변환해 UTC 오프셋이 붙은 ISO 8601 문자열 iso_datetime 으로 돌려준다. "
        "입력은 초 단위(YYYY-MM-DDTHH:MM:SS, 공백 구분 허용, 소수 초 불가)이며 오프셋이 없으면 from_tz 로 "
        "해석하고 있으면 from_tz 를 쓰지 않는다. 서머타임 겹침 시각은 앞선 쪽으로 해석한다."
    ),
    version="1.0.0",
)
def tz_convert(
    iso_datetime: str,
    from_tz: str,
    to_tz: str,
) -> TzConvertResult:
    """Convert a datetime from one IANA timezone to another.

    Args:
        iso_datetime: ISO 8601 datetime string (naive or offset-aware)
        from_tz:      소스 IANA 타임존 (naive 입력 시 적용)
        to_tz:        대상 IANA 타임존

    Returns:
        {iso_datetime: str (with UTC offset), trace}
    """
    trace = CalcTrace(
        tool="datetime.tz_convert",
        formula="result = datetime.astimezone(to_tz)",
    )
    trace.input("iso_datetime", iso_datetime)
    trace.input("from_tz",      from_tz)
    trace.input("to_tz",        to_tz)

    from_zone = _resolve_tz(from_tz)
    to_zone   = _resolve_tz(to_tz)

    dt_from = _parse_iso(iso_datetime, from_zone)
    dt_to   = dt_from.astimezone(to_zone)

    # Format as ISO 8601 with offset (+HH:MM or -HH:MM)
    result_str = dt_to.isoformat()

    trace.step("parsed_from",  str(dt_from))
    trace.step("converted_to", result_str)
    trace.output(result_str)

    return {
        "iso_datetime": result_str,
        "trace":        trace.to_dict(),
    }
