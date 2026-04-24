from __future__ import annotations

import re
import threading
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from typing import Any

from sootool.core.errors import DomainConstraintError, SooToolError
from sootool.core.registry import ToolRegistry

# Non-recursive linear scanner — single finditer, no nested quantifiers.
REF_PATTERN = re.compile(
    r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)(\.[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}"
)

_SNAPSHOT_TTL_S: float = 600.0  # 10 minutes

_PIPELINE_SNAPSHOTS: OrderedDict[str, dict[str, Any]] = OrderedDict()
_SNAPSHOT_LOCK = threading.Lock()


class CircularDependencyError(SooToolError):
    pass


class UnresolvedReferenceError(SooToolError):
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _evict_expired() -> None:
    """Remove snapshots older than TTL. Must be called under _SNAPSHOT_LOCK."""
    now = time.monotonic()
    expired = [pid for pid, snap in _PIPELINE_SNAPSHOTS.items()
               if now - snap["_ts"] > _SNAPSHOT_TTL_S]
    for pid in expired:
        del _PIPELINE_SNAPSHOTS[pid]


def _extract_refs(value: Any) -> list[tuple[str, str]]:
    """Return list of (step_id, dot_path) for all ${step.field...} refs in value."""
    refs: list[tuple[str, str]] = []
    if isinstance(value, str):
        for m in REF_PATTERN.finditer(value):
            refs.append((m.group(1), m.group(2).lstrip(".")))
    elif isinstance(value, dict):
        for v in value.values():
            refs.extend(_extract_refs(v))
    elif isinstance(value, list):
        for v in value:
            refs.extend(_extract_refs(v))
    return refs


def _resolve_refs(value: Any, completed: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, str):
        # Full-match: return the resolved value as its native type
        fm = REF_PATTERN.fullmatch(value)
        if fm:
            step_id = fm.group(1)
            path = fm.group(2).lstrip(".").split(".")
            if step_id not in completed:
                raise UnresolvedReferenceError(f"참조 불가: {step_id}")
            node: Any = completed[step_id]
            for key in path:
                if not isinstance(node, dict) or key not in node:
                    raise UnresolvedReferenceError(
                        f"경로 없음: ${{{step_id}.{'.'.join(path)}}}"
                    )
                node = node[key]
            return node

        def _sub(m: re.Match[str]) -> str:
            step_id = m.group(1)
            path = m.group(2).lstrip(".").split(".")
            if step_id not in completed:
                raise UnresolvedReferenceError(f"참조 불가: {step_id}")
            node: Any = completed[step_id]
            for key in path:
                if not isinstance(node, dict) or key not in node:
                    raise UnresolvedReferenceError(
                        f"경로 없음: ${{{step_id}.{'.'.join(path)}}}"
                    )
                node = node[key]
            return str(node)

        return REF_PATTERN.sub(_sub, value)

    if isinstance(value, dict):
        return {k: _resolve_refs(v, completed) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(v, completed) for v in value]
    return value


def _compute_dag_depth(graph: dict[str, set[str]], order: list[str]) -> int:
    """Compute the length of the longest path in the DAG (1-indexed depth)."""
    depth: dict[str, int] = {}
    for node in order:
        if not graph[node]:
            depth[node] = 1
        else:
            depth[node] = 1 + max(depth[d] for d in graph[node])
    return max(depth.values()) if depth else 0


# ---------------------------------------------------------------------------
# PipelineExecutor
# ---------------------------------------------------------------------------

@dataclass
class PipelineExecutor:
    registry: ToolRegistry
    max_steps: int = 50
    max_depth: int = 10
    step_timeout_s: float = 2.0
    pipeline_timeout_s: float = 30.0

    def run(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        if len(steps) > self.max_steps:
            raise DomainConstraintError(
                f"파이프라인 step 수 {len(steps)} > max_steps {self.max_steps}"
            )

        ids = [s["id"] for s in steps]
        if len(set(ids)) != len(ids):
            raise ValueError("파이프라인 step id 중복")
        by_id = {s["id"]: s for s in steps}

        # Build dependency graph
        graph: dict[str, set[str]] = {s["id"]: set() for s in steps}
        for s in steps:
            for dep_id, _ in _extract_refs(s.get("args", {})):
                if dep_id not in by_id:
                    raise UnresolvedReferenceError(f"정의되지 않은 step 참조: {dep_id}")
                graph[s["id"]].add(dep_id)

        sorter = TopologicalSorter(graph)
        try:
            order = list(sorter.static_order())
        except CycleError as e:
            raise CircularDependencyError(str(e)) from e

        # Check DAG depth
        dag_depth = _compute_dag_depth(graph, order)
        if dag_depth > self.max_depth:
            raise DomainConstraintError(
                f"DAG 깊이 {dag_depth} > max_depth {self.max_depth}"
            )

        return self._execute(steps, by_id, graph, order)

    def _execute(
        self,
        steps: list[dict[str, Any]],
        by_id: dict[str, dict[str, Any]],
        graph: dict[str, set[str]],
        order: list[str],
        seed_completed: dict[str, dict[str, Any]] | None = None,
        from_step: str | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        step_results: dict[str, dict[str, Any]] = {}
        completed: dict[str, dict[str, Any]] = dict(seed_completed or {})

        # Determine which steps to skip (already completed via resume)
        skip_ids: set[str] = set()
        if from_step is not None and seed_completed is not None:
            # Skip all steps that are already in seed_completed AND come before from_step in order
            from_step_idx = order.index(from_step)
            for i, step_id in enumerate(order):
                if i < from_step_idx and step_id in seed_completed:
                    skip_ids.add(step_id)

        pool = ThreadPoolExecutor(max_workers=1)
        try:
            pipeline_deadline_hit = False

            for step_id in order:
                step = by_id[step_id]

                # Remaining steps after a pipeline timeout are marked skipped
                if pipeline_deadline_hit:
                    step_results[step_id] = {
                        "id":    step_id,
                        "tool":  step["tool"],
                        "status": "skipped",
                        "error": {
                            "type":    "PipelineTimeout",
                            "message": f"pipeline_timeout_s={self.pipeline_timeout_s}",
                        },
                    }
                    continue

                # Check pipeline-level deadline before executing this step
                if (time.monotonic() - started) >= self.pipeline_timeout_s:
                    pipeline_deadline_hit = True
                    step_results[step_id] = {
                        "id":    step_id,
                        "tool":  step["tool"],
                        "status": "timeout",
                        "error": {
                            "type":    "PipelineTimeout",
                            "message": f"pipeline_timeout_s={self.pipeline_timeout_s}",
                        },
                        "elapsed_ms": int((time.monotonic() - started) * 1000),
                    }
                    continue

                if step_id in skip_ids:
                    # Reuse seeded result
                    step_results[step_id] = {
                        "id":         step_id,
                        "tool":       step["tool"],
                        "status":     "ok",
                        "result":     completed[step_id]["result"],
                        "elapsed_ms": 0,
                        "reused":     True,
                    }
                    continue

                deps_failed = [
                    d for d in graph[step_id]
                    if step_results.get(d, {}).get("status") not in ("ok",) and d not in skip_ids
                ]
                if deps_failed:
                    step_results[step_id] = {
                        "id":    step_id,
                        "tool":  step["tool"],
                        "status": "skipped",
                        "error": {"type": "DependencyFailed", "message": f"deps: {deps_failed}"},
                    }
                    continue

                try:
                    resolved_args = _resolve_refs(step.get("args", {}), completed)
                    t0 = time.monotonic()
                    fut = pool.submit(self.registry.invoke, step["tool"], **resolved_args)
                    try:
                        res = fut.result(timeout=self.step_timeout_s)
                    except FuturesTimeout:
                        fut.cancel()
                        step_results[step_id] = {
                            "id":    step_id,
                            "tool":  step["tool"],
                            "status": "timeout",
                            "error": {
                                "type":    "TimeoutError",
                                "message": f"step_timeout_s={self.step_timeout_s}",
                            },
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }
                        continue
                    step_results[step_id] = {
                        "id":         step_id,
                        "tool":       step["tool"],
                        "status":     "ok",
                        "result":     res,
                        "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    }
                    completed[step_id] = {"result": res}
                except Exception as e:
                    step_results[step_id] = {
                        "id":    step_id,
                        "tool":  step["tool"],
                        "status": "error",
                        "error": {"type": type(e).__name__, "message": str(e)},
                    }
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        total_ms = int((time.monotonic() - started) * 1000)
        all_ok  = all(r["status"] == "ok" for r in step_results.values())
        any_ok  = any(r["status"] == "ok" for r in step_results.values())
        status  = "ok" if all_ok else ("failed" if not any_ok else "partial")

        pipeline_id = uuid.uuid4().hex
        snapshot = {
            "_ts":       time.monotonic(),
            "steps":     steps,
            "by_id":     by_id,
            "graph":     graph,
            "order":     order,
            "completed": {
                sid: completed[sid] for sid in completed
            },
        }
        with _SNAPSHOT_LOCK:
            _evict_expired()
            _PIPELINE_SNAPSHOTS[pipeline_id] = snapshot

        return {
            "status":        status,
            "steps":         step_results,
            "total_time_ms": total_ms,
            "order":         order,
            "pipeline_id":   pipeline_id,
        }


# ---------------------------------------------------------------------------
# Resume API
# ---------------------------------------------------------------------------

def get_pipeline_snapshot(pipeline_id: str) -> dict[str, Any] | None:
    with _SNAPSHOT_LOCK:
        _evict_expired()
        return _PIPELINE_SNAPSHOTS.get(pipeline_id)


def resume_pipeline(
    pipeline_id: str,
    from_step: str,
    registry: ToolRegistry,
) -> dict[str, Any]:
    snap = get_pipeline_snapshot(pipeline_id)
    if snap is None:
        raise KeyError(f"파이프라인 스냅샷 없음: {pipeline_id}")

    steps    = snap["steps"]
    by_id    = snap["by_id"]
    graph    = snap["graph"]
    order    = snap["order"]
    completed_seed = snap["completed"]

    if from_step not in by_id:
        raise KeyError(f"step 없음: {from_step}")

    ex = PipelineExecutor(registry=registry)
    return ex._execute(
        steps=steps,
        by_id=by_id,
        graph=graph,
        order=order,
        seed_completed=completed_seed,
        from_step=from_step,
    )
