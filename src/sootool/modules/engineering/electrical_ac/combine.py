"""Capacitor and inductor network combination tools.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
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


@REGISTRY.tool(
    namespace="engineering",
    name="capacitor_combine",
    description=(
        "커패시터 직렬/병렬 합성. "
        "series: 1/C = Σ(1/Cᵢ), parallel: C = ΣCᵢ."
    ),
    version="1.0.0",
)
def capacitor_combine(capacitors: list[str], topology: str) -> dict[str, Any]:
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
        "인덕터 직렬/병렬 합성. "
        "series: L = ΣLᵢ, parallel: 1/L = Σ(1/Lᵢ)."
    ),
    version="1.0.0",
)
def inductor_combine(inductors: list[str], topology: str) -> dict[str, Any]:
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
