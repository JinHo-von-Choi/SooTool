from __future__ import annotations

import time

import pytest

from sootool.core.registry import ToolRegistry
from sootool.core.batch import BatchExecutor, BatchLimitError


def _make_registry() -> ToolRegistry:
    r = ToolRegistry()

    @r.tool(namespace="t", name="add")
    def _add(a: str, b: str) -> dict:
        from decimal import Decimal
        return {"result": str(Decimal(a) + Decimal(b))}

    @r.tool(namespace="t", name="boom")
    def _boom() -> dict:
        raise ValueError("terrible")

    @r.tool(namespace="t", name="slow")
    def _slow(seconds: float) -> dict:
        time.sleep(seconds)
        return {"result": "ok"}

    return r


def test_batch_runs_independent_items():
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0)
    out = ex.run(items=[
        {"id": "a", "tool": "t.add", "args": {"a": "1", "b": "2"}},
        {"id": "b", "tool": "t.add", "args": {"a": "10", "b": "20"}},
    ])
    assert out["status"] == "all_ok"
    by_id = {r["id"]: r for r in out["results"]}
    assert by_id["a"]["status"] == "ok"
    assert by_id["a"]["result"]["result"] == "3"
    assert by_id["b"]["result"]["result"] == "30"


def test_batch_isolates_failure_per_item():
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0)
    out = ex.run(items=[
        {"id": "ok", "tool": "t.add", "args": {"a": "1", "b": "2"}},
        {"id": "fail", "tool": "t.boom", "args": {}},
    ])
    assert out["status"] == "partial"
    by_id = {r["id"]: r for r in out["results"]}
    assert by_id["ok"]["status"] == "ok"
    assert by_id["fail"]["status"] == "error"
    assert by_id["fail"]["error"]["type"] == "ValueError"
    assert "terrible" in by_id["fail"]["error"]["message"]


def test_batch_item_timeout():
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=10, item_timeout_s=0.05, batch_timeout_s=5.0)
    out = ex.run(items=[{"id": "s", "tool": "t.slow", "args": {"seconds": 0.3}}])
    assert out["results"][0]["status"] == "timeout"


def test_batch_rejects_over_max_items():
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=2, item_timeout_s=5.0, batch_timeout_s=30.0)
    with pytest.raises(BatchLimitError):
        ex.run(items=[{"id": str(i), "tool": "t.add", "args": {"a": "1", "b": "1"}} for i in range(3)])


def test_batch_duplicate_ids_rejected():
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0)
    with pytest.raises(ValueError, match="중복"):
        ex.run(items=[
            {"id": "x", "tool": "t.add", "args": {"a": "1", "b": "1"}},
            {"id": "x", "tool": "t.add", "args": {"a": "1", "b": "1"}},
        ])


def test_batch_metadata():
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=10, item_timeout_s=5.0, batch_timeout_s=30.0)
    out = ex.run(items=[{"id": "a", "tool": "t.add", "args": {"a": "1", "b": "2"}}])
    assert "total_time_ms" in out
    assert "parallelism" in out
    assert out["count_ok"] == 1
    assert out["count_error"] == 0
    assert out["count_timeout"] == 0


def test_batch_deterministic_preserves_input_order():
    """With deterministic=True (default), results must be in the same order as input items."""
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0, deterministic=True)
    input_ids = ["z", "a", "m"]
    out = ex.run(items=[
        {"id": "z", "tool": "t.add", "args": {"a": "1", "b": "1"}},
        {"id": "a", "tool": "t.add", "args": {"a": "2", "b": "2"}},
        {"id": "m", "tool": "t.add", "args": {"a": "3", "b": "3"}},
    ])
    result_ids = [r["id"] for r in out["results"]]
    assert result_ids == input_ids, f"Expected {input_ids}, got {result_ids}"
    assert "non_deterministic" not in out


def test_batch_non_deterministic_flag():
    """With deterministic=False, response must include non_deterministic=True."""
    r = _make_registry()
    ex = BatchExecutor(registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0, deterministic=False)
    out = ex.run(items=[
        {"id": "p", "tool": "t.add", "args": {"a": "1", "b": "1"}},
        {"id": "q", "tool": "t.add", "args": {"a": "2", "b": "2"}},
    ])
    assert out["non_deterministic"] is True
