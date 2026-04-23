from __future__ import annotations

import time

import pytest

from sootool.core.batch import BatchExecutor, BatchLimitError
from sootool.core.registry import ToolRegistry


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


def test_batch_deterministic_wall_clock_bounded_by_max_item(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-020 회귀 테스트.

    deterministic=True 경로에서도 as_completed 기반 수집으로 wall-clock 이
    max(item_time) 수준에 근접해야 한다. 특히 가장 느린 item 이 입력 id 기준
    앞쪽에 있어도, 뒤따르는 빠른 item 들의 수집이 선행 item 의 완료를 기다리지
    않아야 한다.
    """
    r = _make_registry()
    ex = BatchExecutor(
        registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0, deterministic=True,
    )
    # 첫 item 은 0.3s, 나머지 9개는 0.05s. 순차 수집이라면 wall-clock >= 0.3 + 9*0.05 = 0.75s.
    # as_completed 수집이라면 wall-clock ~= max(0.3, 0.05*ceil(9/workers))
    items = [{"id": "slow", "tool": "t.slow", "args": {"seconds": 0.3}}]
    items += [
        {"id": f"fast-{i}", "tool": "t.slow", "args": {"seconds": 0.05}}
        for i in range(9)
    ]
    t0 = time.monotonic()
    out = ex.run(items=items)
    wall = time.monotonic() - t0

    # 입력 id 순서 불변
    assert [r["id"] for r in out["results"]] == [it["id"] for it in items]
    # 전부 성공
    assert out["count_ok"] == 10
    # 순차 수집 대비 단축: 느슨한 상한(0.6s). 순차였다면 >= 0.75s.
    assert wall < 0.6, f"wall-clock {wall:.3f}s > 0.6s — 순차 수집 회귀 가능성"


def test_batch_deterministic_order_independent_of_completion() -> None:
    """ADR-011 invariant 재확인.

    완료 순서가 입력 역순이 되도록 구성해도 results 는 입력 id 순서로 반환.
    """
    r = _make_registry()
    ex = BatchExecutor(
        registry=r, max_items=100, item_timeout_s=5.0, batch_timeout_s=30.0, deterministic=True,
    )
    # 입력 순서: [a, b, c] 이지만 소요 시간은 a 가 가장 길다 → 완료 순서 c, b, a.
    items = [
        {"id": "a", "tool": "t.slow", "args": {"seconds": 0.25}},
        {"id": "b", "tool": "t.slow", "args": {"seconds": 0.10}},
        {"id": "c", "tool": "t.slow", "args": {"seconds": 0.02}},
    ]
    out = ex.run(items=items)
    assert [r["id"] for r in out["results"]] == ["a", "b", "c"]
    assert all(r["status"] == "ok" for r in out["results"])
