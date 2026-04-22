"""
tests/core/test_traps.py — Trap defense tests.

Documents known precision/serialization/concurrency traps in SooTool
and verifies that each trap is properly guarded.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import json
from decimal import Decimal

# ---------------------------------------------------------------------------
# Group 1: Pint Quantity JSON serialization trap
# ---------------------------------------------------------------------------

def test_quantity_direct_json_fails() -> None:
    """Direct json.dumps of a pint Quantity raises TypeError — never pass Quantity into JSON."""
    from sootool.core.units import Q

    q = Q("1.5", "meter")
    try:
        json.dumps(q)
        raise AssertionError("Expected TypeError")
    except TypeError:
        pass


def test_quantity_snapshot_roundtrip_safe() -> None:
    """quantity_to_snapshot / snapshot_to_quantity roundtrip is JSON-safe and lossless."""
    from sootool.core.cast import quantity_to_snapshot, snapshot_to_quantity
    from sootool.core.units import Q

    q          = Q("1.5", "meter")
    snap       = quantity_to_snapshot(q)
    serialized = json.dumps(snap)
    restored   = snapshot_to_quantity(json.loads(serialized))

    assert restored.magnitude == q.magnitude
    assert str(restored.units) == str(q.units)


# ---------------------------------------------------------------------------
# Group 2: JSON float leakage trap
# ---------------------------------------------------------------------------

def test_json_default_loses_float_precision() -> None:
    """Standard json.loads returns float for numeric values — precision is not preserved."""
    d = json.loads('{"x": 0.1}')
    assert isinstance(d["x"], float)  # float leaks


def test_json_with_decimal_parser_preserves() -> None:
    """_parse_request_json uses parse_float=Decimal so 0.1 stays exact."""
    from sootool.server import _parse_request_json

    d = _parse_request_json('{"x": 0.1}')
    assert isinstance(d["x"], Decimal)
    assert d["x"] == Decimal("0.1")


# ---------------------------------------------------------------------------
# Group 3: Pipeline resume TTL behavior
# ---------------------------------------------------------------------------

def test_pipeline_resume_missing_id_raises() -> None:
    """resume_pipeline raises a clear error for unknown pipeline IDs."""
    from sootool.core.pipeline import resume_pipeline
    from sootool.core.registry import ToolRegistry

    r = ToolRegistry()
    try:
        resume_pipeline("nonexistent_id_abc", "s1", r)
        raise AssertionError("Expected error")
    except (KeyError, Exception) as e:
        msg = str(e).lower()
        assert (
            "nonexistent_id_abc" in str(e)
            or "not found" in msg
            or "pipeline" in msg
            or "snapshot" in msg
        )


def test_pipeline_resume_returns_reused_results() -> None:
    """resume_pipeline replays from an intermediate step reusing earlier results."""
    from sootool.core.pipeline import PipelineExecutor, resume_pipeline
    from sootool.core.registry import ToolRegistry

    r = ToolRegistry()

    @r.tool(namespace="t", name="add_resume")
    def _add(a: str, b: str) -> dict:
        return {"result": str(Decimal(a) + Decimal(b))}

    ex  = PipelineExecutor(registry=r)
    out = ex.run(steps=[
        {"id": "s1", "tool": "t.add_resume", "args": {"a": "1", "b": "2"}},
        {"id": "s2", "tool": "t.add_resume", "args": {"a": "${s1.result.result}", "b": "10"}},
    ])

    pid     = out["pipeline_id"]
    resumed = resume_pipeline(pid, "s2", r)

    assert resumed["steps"]["s2"]["result"]["result"] == "13"
    # s1 should be marked as reused, not re-executed
    assert resumed["steps"]["s1"].get("reused") is True


# ---------------------------------------------------------------------------
# Group 4: KRWMoney compound operation accumulated error
# ---------------------------------------------------------------------------

def test_krw_sum_then_round_vs_round_then_sum_differ() -> None:
    """Round-then-sum and sum-then-round produce different totals — order matters."""
    from sootool.core.locale_kr import KRWMoney
    from sootool.core.rounding import RoundingPolicy

    a = KRWMoney(Decimal("123"), rounding=RoundingPolicy.DOWN, unit=10).to_decimal()  # 120
    b = KRWMoney(Decimal("456"), rounding=RoundingPolicy.DOWN, unit=10).to_decimal()  # 450
    c = KRWMoney(Decimal("789"), rounding=RoundingPolicy.DOWN, unit=10).to_decimal()  # 780
    round_then_sum = a + b + c  # 1350

    raw_sum        = Decimal("123") + Decimal("456") + Decimal("789")  # 1368
    sum_then_round = (raw_sum // 10) * 10  # 1360

    assert round_then_sum != sum_then_round
    assert abs(round_then_sum - sum_then_round) >= 10


def test_krwmoney_unit_10_aggregate_correct() -> None:
    """HALF_UP + unit=10: construction-rounding then addition yields deterministic total."""
    from sootool.core.locale_kr import KRWMoney
    from sootool.core.rounding import RoundingPolicy

    a     = KRWMoney(Decimal("123"), rounding=RoundingPolicy.HALF_UP, unit=10)
    b     = KRWMoney(Decimal("456"), rounding=RoundingPolicy.HALF_UP, unit=10)
    c     = KRWMoney(Decimal("789"), rounding=RoundingPolicy.HALF_UP, unit=10)
    total = a + b + c  # 120 + 460 + 790 path -> 1370

    assert total.to_decimal() == Decimal("1370")


# ---------------------------------------------------------------------------
# Group 5: Batch N=100 deterministic ordering race test
# ---------------------------------------------------------------------------

def test_batch_100_parallel_deterministic_order() -> None:
    """100-item parallel batch returns results in exact input order regardless of execution order."""
    import random
    import time

    from sootool.core.batch import BatchExecutor
    from sootool.core.registry import ToolRegistry

    r = ToolRegistry()

    @r.tool(namespace="t", name="identity_det")
    def _id(value: str) -> dict:
        time.sleep(random.random() * 0.01)  # noqa: S311 — deliberate non-crypto random for race stress
        return {"v": value}

    ex    = BatchExecutor(registry=r, max_items=200, item_timeout_s=5.0, batch_timeout_s=30.0)
    items = [
        {"id": f"item_{i:03d}", "tool": "t.identity_det", "args": {"value": str(i)}}
        for i in range(100)
    ]
    out = ex.run(items=items)

    assert out["status"] == "all_ok"
    for i, result in enumerate(out["results"]):
        assert result["id"] == f"item_{i:03d}"
        assert result["result"]["v"] == str(i)


def test_batch_100_non_deterministic_flag() -> None:
    """non_deterministic=True flag appears in response and all 100 items succeed."""
    from sootool.core.batch import BatchExecutor
    from sootool.core.registry import ToolRegistry

    r = ToolRegistry()

    @r.tool(namespace="t", name="identity_ndet")
    def _id(value: str) -> dict:
        return {"v": value}

    ex    = BatchExecutor(
        registry=r,
        max_items=200,
        item_timeout_s=5.0,
        batch_timeout_s=30.0,
        deterministic=False,
    )
    items = [
        {"id": f"item_{i:03d}", "tool": "t.identity_ndet", "args": {"value": str(i)}}
        for i in range(100)
    ]
    out = ex.run(items=items)

    assert out.get("non_deterministic") is True
    assert out["count_ok"] == 100
