"""Earned Schedule (ES) — time-based complement to EVM.

내부 자료형 (ADR-008): 전 구간 Decimal (시간 단위 동일).

핵심 식:
- ES(t): EV 를 기준선에서 처음으로 달성한 시점 (PV 타임라인 역산).
- SPI(t) = ES / AT  (시간 기반 SPI, 단위 없음)
- TSPI  = (BAC - EV) / (BAC - EV_at_AT)  — 표준 정의를 단순화해 남은 작업 대비 남은 시간 효율성 지표로 사용하지 않고,
          여기서는 시간 기반 TSPI(t) = (PD - ES) / (PD - AT) 를 사용 (Lipke 2003).
- IEAC(t) = PD / SPI(t)  — Lipke. PD=Planned Duration.

PV 타임라인은 step-function 또는 부분 선형으로 가정: (시간, 누적 PV) 쌍 리스트.

출처:
- Lipke W. "Schedule is Different." The Measurable News, 2003.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) Decimal 문자열이어야 합니다: {value!r}") from exc


def _earned_schedule(
    pv_timeline: list[tuple[Decimal, Decimal]],
    ev:          Decimal,
) -> Decimal:
    """Inverse-lookup: find time t_es such that PV(t_es) == EV (linear interpolation)."""
    if not pv_timeline:
        raise InvalidInputError("pv_timeline이 비어 있습니다.")
    # Must be sorted by time ascending. Validate monotonic non-decreasing PV.
    for i in range(1, len(pv_timeline)):
        if pv_timeline[i][0] <= pv_timeline[i - 1][0]:
            raise DomainConstraintError("pv_timeline은 시간 오름차순이어야 합니다.")
        if pv_timeline[i][1] < pv_timeline[i - 1][1]:
            raise DomainConstraintError("pv_timeline의 누적 PV는 단조 비감소여야 합니다.")

    if ev <= pv_timeline[0][1]:
        return pv_timeline[0][0]
    if ev >= pv_timeline[-1][1]:
        return pv_timeline[-1][0]

    # Linear interpolation between surrounding points
    for i in range(1, len(pv_timeline)):
        t1, pv1 = pv_timeline[i - 1]
        t2, pv2 = pv_timeline[i]
        if pv1 <= ev <= pv2:
            if pv2 == pv1:
                return t1
            frac = (ev - pv1) / (pv2 - pv1)
            return t1 + frac * (t2 - t1)
    raise DomainConstraintError("EV가 pv_timeline 범위를 벗어났습니다.")  # pragma: no cover


@REGISTRY.tool(
    namespace="pm",
    name="earned_schedule",
    description=(
        "Earned Schedule: SPI(t)=ES/AT, TSPI(t)=(PD-ES)/(PD-AT), IEAC(t)=PD/SPI(t). "
        "pv_timeline은 [{time: '...', cumulative_pv: '...'}] 시간 오름차순."
    ),
    version="1.0.0",
)
def earned_schedule(
    pv_timeline:       list[dict[str, str]],
    earned_value:      str,
    actual_time:       str,
    planned_duration:  str,
) -> dict[str, Any]:
    """Compute Earned Schedule metrics.

    Args:
        pv_timeline:      List of {"time": Decimal str, "cumulative_pv": Decimal str}, ascending.
        earned_value:     Current EV (Decimal string).
        actual_time:      Elapsed time AT (Decimal string, same unit as pv_timeline.time).
        planned_duration: PD — planned total duration (Decimal string).

    Returns:
        {es, spi_t, tspi_t, ieac_t, trace}
    """
    trace = CalcTrace(
        tool="pm.earned_schedule",
        formula="ES: PV⁻¹(EV); SPI(t)=ES/AT; TSPI(t)=(PD-ES)/(PD-AT); IEAC(t)=PD/SPI(t)",
    )
    if not isinstance(pv_timeline, list) or not pv_timeline:
        raise InvalidInputError("pv_timeline은 비어있지 않은 리스트여야 합니다.")
    points: list[tuple[Decimal, Decimal]] = []
    for i, row in enumerate(pv_timeline):
        if not isinstance(row, dict) or "time" not in row or "cumulative_pv" not in row:
            raise InvalidInputError(
                f"pv_timeline[{i}]은 {{'time','cumulative_pv'}} 필드를 가져야 합니다."
            )
        points.append((_parse_decimal(row["time"], f"time[{i}]"),
                       _parse_decimal(row["cumulative_pv"], f"cumulative_pv[{i}]")))

    ev = _parse_decimal(earned_value,     "earned_value")
    at = _parse_decimal(actual_time,      "actual_time")
    pd = _parse_decimal(planned_duration, "planned_duration")

    if at <= D("0"):
        raise DomainConstraintError(f"actual_time은 양수여야 합니다: {actual_time}")
    if pd <= D("0"):
        raise DomainConstraintError(f"planned_duration은 양수여야 합니다: {planned_duration}")

    trace.input("pv_timeline_points", len(points))
    trace.input("earned_value",     earned_value)
    trace.input("actual_time",      actual_time)
    trace.input("planned_duration", planned_duration)

    es    = _earned_schedule(points, ev)
    spi_t = es / at
    ieac_t = pd / spi_t if spi_t != D("0") else D("0")

    if pd == at:
        tspi_t = D("0")  # avoid div-by-zero; caller should interpret
    else:
        tspi_t = (pd - es) / (pd - at)

    trace.step("ES",     str(es))
    trace.step("SPI_t",  str(spi_t))
    trace.step("TSPI_t", str(tspi_t))
    trace.step("IEAC_t", str(ieac_t))
    trace.output({
        "es":     str(es),
        "spi_t":  str(spi_t),
        "tspi_t": str(tspi_t),
        "ieac_t": str(ieac_t),
    })

    return {
        "es":     str(es),
        "spi_t":  str(spi_t),
        "tspi_t": str(tspi_t),
        "ieac_t": str(ieac_t),
        "trace":  trace.to_dict(),
    }
