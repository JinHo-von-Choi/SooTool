"""Pregnancy gestational age and EDD calculator.

Author: 최진호
Date: 2026-04-22

Source:
  American College of Obstetricians and Gynecologists (ACOG).
  Methods for Estimating the Due Date. Committee Opinion No. 700. May 2017.
  - EDD = LMP + 280 days (Naegele's rule)
  - Post-term defined as >= 42 weeks (ACOG)
  - Trimester boundaries: T1 1-13w, T2 14-27w, T3 28+w
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_EDD_DAYS       = 280
_POST_TERM_DAYS = 294   # 42 weeks

_T1_MAX_DAYS = 97   # up to end of week 13 (91 days + 6 days → 97 days inclusive end)
_T2_MAX_DAYS = 195  # up to end of week 27 (189 + 6 → 195)


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise InvalidInputError(
            f"날짜 형식이 올바르지 않습니다 (YYYY-MM-DD 필요): {s!r}"
        ) from exc


def _trimester(total_days: int) -> int:
    """Return trimester 1/2/3 from total gestational days from LMP."""
    weeks = total_days // 7
    if weeks < 14:
        return 1
    if weeks < 28:
        return 2
    return 3


@REGISTRY.tool(
    namespace="medical",
    name="pregnancy_weeks",
    description=(
        "임신 주수 및 분만예정일(EDD) 계산. "
        "LMP 기준 Naegele 법칙: EDD = LMP + 280일. "
        "최대 42주(ACOG post-term 기준)에서 클램프."
    ),
    version="1.0.0",
)
def medical_pregnancy_weeks(
    lmp_date:       str,
    reference_date: str | None = None,
) -> dict[str, Any]:
    """Calculate gestational age and EDD.

    Args:
        lmp_date:       최종 월경일 (YYYY-MM-DD)
        reference_date: 기준일 (YYYY-MM-DD, 기본값: 오늘 UTC)

    Returns:
        {weeks: int, days: int, trimester: int, edd: str (YYYY-MM-DD), trace}
    """
    trace = CalcTrace(
        tool="medical.pregnancy_weeks",
        formula=(
            "total_days = reference_date - lmp_date; "
            "weeks = total_days // 7; days = total_days % 7; "
            "EDD = lmp_date + 280 days; clamp 0-42 weeks"
        ),
    )

    lmp = _parse_date(lmp_date)

    if reference_date is not None:
        ref = _parse_date(reference_date)
    else:
        ref = date.today()

    if lmp > ref:
        raise InvalidInputError("lmp_date는 reference_date 이전이어야 합니다.")

    trace.input("lmp_date",       lmp_date)
    trace.input("reference_date", str(ref))

    edd_date  = lmp + timedelta(days=_EDD_DAYS)
    raw_delta = (ref - lmp).days

    # Clamp to 0-42 weeks
    clamped_delta = max(0, min(raw_delta, _POST_TERM_DAYS))

    weeks     = clamped_delta // 7
    days      = clamped_delta % 7
    trimester = _trimester(clamped_delta)
    clamped   = raw_delta > _POST_TERM_DAYS or raw_delta < 0

    trace.step("raw_delta_days", str(raw_delta))
    trace.step("clamped",        str(clamped))
    trace.step("edd",            str(edd_date))
    trace.output(f"{weeks}w{days}d")

    return {
        "weeks":     weeks,
        "days":      days,
        "trimester": trimester,
        "edd":       str(edd_date),
        "trace":     trace.to_dict(),
    }
