"""Capacitor and inductor network combination tools.
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.engineering.electrical_ac._common import (
    _ONE,
    _ZERO,
)


def _combine_network(
    values: list[str],
    topology: str,
    series_rule: str,   # "sum" or "reciprocal"
    parallel_rule: str,
    label: str,
) -> Decimal:
    if not values:
        raise InvalidInputError(f"{label} 리스트는 최소 1개 이상이어야 합니다.")
    decs = [D(v) for v in values]
    for i, v in enumerate(decs):
        if v <= _ZERO:
            raise InvalidInputError(f"{label}[{i}]는 0 초과여야 합니다. 입력값: {values[i]!r}")
    if topology not in ("series", "parallel"):
        raise InvalidInputError("topology는 'series' 또는 'parallel'이어야 합니다.")

    rule = series_rule if topology == "series" else parallel_rule
    if rule == "sum":
        return add(*decs)
    # reciprocal
    reciprocal_sum = add(*[div(_ONE, v) for v in decs])
    return div(_ONE, reciprocal_sum)


class CombineResult(TracedResult):
    """합성 결과. total 은 Decimal 문자열."""

    total: str


@REGISTRY.tool(
    namespace="engineering",
    name="capacitor_combine",
    description=(
        "커패시터 여러 개의 합성 정전용량을 구한다. topology='series'면 1/C=Σ(1/Cᵢ), "
        "'parallel'이면 C=ΣCᵢ. capacitors 는 0 초과 정전용량(F)의 Decimal 문자열 목록이며 "
        "최소 1개, total 은 입력과 같은 단위. 계산은 유효숫자 50자리 Decimal. "
        "오용 주의: 저항과 인덕터는 직렬 병렬 공식이 반대다."
    ),
    version="1.0.0",
)
def capacitor_combine(capacitors: list[str], topology: str) -> CombineResult:
    """Compute equivalent capacitance."""
    trace = CalcTrace(
        tool="engineering.capacitor_combine",
        formula="series: 1/C = Σ(1/Cᵢ); parallel: C = ΣCᵢ",
    )
    trace.input("capacitors", capacitors)
    trace.input("topology",   topology)

    total = _combine_network(
        capacitors,
        topology,
        series_rule="reciprocal",
        parallel_rule="sum",
        label="capacitors",
    )
    trace.step("total", str(total))
    trace.output(str(total))

    return {"total": str(total), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="engineering",
    name="inductor_combine",
    description=(
        "인덕터 여러 개의 합성 인덕턴스를 구한다. topology='series'면 L=ΣLᵢ, "
        "'parallel'이면 1/L=Σ(1/Lᵢ). inductors 는 0 초과 인덕턴스(H)의 Decimal 문자열 목록이며 "
        "최소 1개, total 은 입력과 같은 단위. 상호 인덕턴스는 고려하지 않는다. "
        "오용 주의: 커패시터는 직렬 병렬 공식이 반대다."
    ),
    version="1.0.0",
)
def inductor_combine(inductors: list[str], topology: str) -> CombineResult:
    """Compute equivalent inductance."""
    trace = CalcTrace(
        tool="engineering.inductor_combine",
        formula="series: L = ΣLᵢ; parallel: 1/L = Σ(1/Lᵢ)",
    )
    trace.input("inductors", inductors)
    trace.input("topology",  topology)

    total = _combine_network(
        inductors,
        topology,
        series_rule="sum",
        parallel_rule="reciprocal",
        label="inductors",
    )
    trace.step("total", str(total))
    trace.output(str(total))

    return {"total": str(total), "trace": trace.to_dict()}
