"""PM Critical Path Method (CPM) tool.

내부 자료형:
- 기간(duration): Decimal 연산.
- 위상 정렬: stdlib graphlib.TopologicalSorter.
- ES, EF, LS, LF, slack: Decimal.

Forward pass:  ES(v) = max(EF(predecessors)), EF = ES + duration.
Backward pass: LF(v) = min(LS(successors)),  LS = LF - duration.
Slack = LS - ES = LF - EF (both equivalent; slack == 0 iff critical).

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from graphlib import CycleError, TopologicalSorter
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="pm",
    name="critical_path",
    description=(
        "주공정법(CPM): ES/EF/LS/LF/slack 계산, 주공정 식별. "
        "graphlib.TopologicalSorter 사용. 사이클 시 DomainConstraintError."
    ),
    version="1.0.0",
)
def critical_path(
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute the Critical Path for a project network.

    Args:
        tasks: List of task dicts, each with:
               - id:           str   — unique task identifier.
               - duration:     str   — Decimal duration (same unit for all).
               - predecessors: list[str] — task IDs that must finish before this starts.

    Returns:
        {critical_path: list[str], total_duration: str,
         task_details: list[{id, es, ef, ls, lf, slack}], trace}

    Raises:
        DomainConstraintError: If a cycle is detected in the dependency graph.
        InvalidInputError:     On malformed input or unknown predecessor IDs.
    """
    trace = CalcTrace(
        tool="pm.critical_path",
        formula="ES=max(EF(preds)), EF=ES+dur; LF=min(LS(succs)), LS=LF-dur; slack=LS-ES",
    )

    if not tasks:
        raise InvalidInputError("tasks 목록이 비어 있습니다.")

    # Parse and validate tasks
    task_ids: set[str]        = set()
    durations: dict[str, Decimal] = {}
    preds_map: dict[str, list[str]] = {}

    for t in tasks:
        tid  = str(t.get("id", ""))
        dur  = str(t.get("duration", "0"))
        preds = list(t.get("predecessors", []))

        if not tid:
            raise InvalidInputError("task id가 비어 있습니다.")
        if tid in task_ids:
            raise InvalidInputError(f"중복 task id: {tid!r}")

        task_ids.add(tid)
        durations[tid] = _parse_decimal(dur, f"task {tid} duration")
        if durations[tid] < D("0"):
            raise DomainConstraintError(f"task {tid}의 duration은 음수가 될 수 없습니다.")
        preds_map[tid] = [str(p) for p in preds]

    # Validate predecessor references
    for tid, preds in preds_map.items():
        for p in preds:
            if p not in task_ids:
                raise InvalidInputError(f"task {tid!r}의 predecessor {p!r}가 존재하지 않습니다.")

    trace.input("task_count", len(tasks))

    # Build graph for topological sort: {node: {dependencies}}
    graph: dict[str, set[str]] = {tid: set(preds_map[tid]) for tid in task_ids}

    try:
        sorter = TopologicalSorter(graph)
        topo_order: list[str] = list(sorter.static_order())
    except CycleError as exc:
        raise DomainConstraintError(
            f"작업 의존성 그래프에 사이클이 존재합니다: {exc}"
        ) from exc

    # Forward pass: compute ES and EF
    es: dict[str, Decimal] = {}
    ef: dict[str, Decimal] = {}

    for tid in topo_order:
        if preds_map[tid]:
            es[tid] = max(ef[p] for p in preds_map[tid])
        else:
            es[tid] = D("0")
        ef[tid] = es[tid] + durations[tid]

    total_duration = max(ef.values())
    trace.step("total_duration", str(total_duration))

    # Backward pass: compute LF and LS
    lf: dict[str, Decimal] = {}
    ls: dict[str, Decimal] = {}

    # Build successors map for backward pass
    succs: dict[str, list[str]] = {tid: [] for tid in task_ids}
    for tid, preds in preds_map.items():
        for p in preds:
            succs[p].append(tid)

    for tid in reversed(topo_order):
        if succs[tid]:
            lf[tid] = min(ls[s] for s in succs[tid])
        else:
            lf[tid] = total_duration
        ls[tid] = lf[tid] - durations[tid]

    # Compute slack and identify critical path (slack == 0)
    slack: dict[str, Decimal] = {tid: ls[tid] - es[tid] for tid in task_ids}
    critical_ids = [tid for tid in topo_order if slack[tid] == D("0")]

    task_details = [
        {
            "id":    tid,
            "es":    str(es[tid]),
            "ef":    str(ef[tid]),
            "ls":    str(ls[tid]),
            "lf":    str(lf[tid]),
            "slack": str(slack[tid]),
        }
        for tid in topo_order
    ]

    trace.step("critical_path", critical_ids)
    trace.output({
        "critical_path":   critical_ids,
        "total_duration":  str(total_duration),
        "task_count":      len(task_details),
    })

    return {
        "critical_path":  critical_ids,
        "total_duration": str(total_duration),
        "task_details":   task_details,
        "trace":          trace.to_dict(),
    }
