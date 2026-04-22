from __future__ import annotations

import pytest

from sootool.core.errors import DomainConstraintError
from sootool.core.pipeline import (
    CircularDependencyError,
    PipelineExecutor,
    UnresolvedReferenceError,
)
from sootool.core.registry import ToolRegistry


def _make_registry() -> ToolRegistry:
    r = ToolRegistry()

    @r.tool(namespace="t", name="add")
    def _add(a: str, b: str) -> dict:
        from decimal import Decimal
        return {"result": str(Decimal(a) + Decimal(b))}

    @r.tool(namespace="t", name="mul")
    def _mul(a: str, b: str) -> dict:
        from decimal import Decimal
        return {"result": str(Decimal(a) * Decimal(b))}

    return r


def test_pipeline_linear_chain():
    r = _make_registry()
    ex = PipelineExecutor(registry=r)
    out = ex.run(steps=[
        {"id": "s1", "tool": "t.add", "args": {"a": "10", "b": "20"}},
        {"id": "s2", "tool": "t.mul", "args": {"a": "${s1.result.result}", "b": "2"}},
    ])
    assert out["status"] == "ok"
    assert out["steps"]["s1"]["result"]["result"] == "30"
    assert out["steps"]["s2"]["result"]["result"] == "60"


def test_pipeline_dag_parallel_branches():
    r = _make_registry()
    ex = PipelineExecutor(registry=r)
    out = ex.run(steps=[
        {"id": "a", "tool": "t.add", "args": {"a": "1", "b": "2"}},
        {"id": "b", "tool": "t.add", "args": {"a": "3", "b": "4"}},
        {"id": "c", "tool": "t.mul", "args": {"a": "${a.result.result}", "b": "${b.result.result}"}},
    ])
    assert out["steps"]["c"]["result"]["result"] == "21"


def test_pipeline_rejects_cycle():
    r = _make_registry()
    ex = PipelineExecutor(registry=r)
    with pytest.raises(CircularDependencyError):
        ex.run(steps=[
            {"id": "x", "tool": "t.add", "args": {"a": "${y.result.result}", "b": "1"}},
            {"id": "y", "tool": "t.add", "args": {"a": "${x.result.result}", "b": "1"}},
        ])


def test_pipeline_rejects_undefined_ref():
    r = _make_registry()
    ex = PipelineExecutor(registry=r)
    with pytest.raises(UnresolvedReferenceError):
        ex.run(steps=[
            {"id": "s", "tool": "t.add", "args": {"a": "${missing.result.result}", "b": "1"}},
        ])


def test_pipeline_aborts_on_dependency_failure():
    r = _make_registry()

    @r.tool(namespace="t", name="boom")
    def _boom() -> dict:
        raise RuntimeError("x")

    ex = PipelineExecutor(registry=r)
    out = ex.run(steps=[
        {"id": "s1", "tool": "t.boom", "args": {}},
        {"id": "s2", "tool": "t.add", "args": {"a": "${s1.result.result}", "b": "1"}},
    ])
    assert out["status"] == "failed"
    assert out["steps"]["s1"]["status"] == "error"
    assert out["steps"]["s2"]["status"] == "skipped"


def test_pipeline_rejects_too_many_steps():
    """51 steps must raise DomainConstraintError mentioning max_steps."""
    r = _make_registry()
    ex = PipelineExecutor(registry=r, max_steps=50)
    steps = [{"id": f"s{i}", "tool": "t.add", "args": {"a": "1", "b": "1"}} for i in range(51)]
    with pytest.raises(DomainConstraintError, match="max_steps"):
        ex.run(steps=steps)


def test_pipeline_resume_reuses_completed_steps():
    """After a successful run, resume(pipeline_id, 'step2') re-executes from step2
    but reuses predecessor results stored in the snapshot."""
    r = _make_registry()
    ex = PipelineExecutor(registry=r)

    steps = [
        {"id": "step1", "tool": "t.add", "args": {"a": "5", "b": "5"}},
        {"id": "step2", "tool": "t.mul", "args": {"a": "${step1.result.result}", "b": "3"}},
        {"id": "step3", "tool": "t.add", "args": {"a": "${step2.result.result}", "b": "1"}},
    ]
    out = ex.run(steps=steps)
    assert out["status"] == "ok"
    pipeline_id = out["pipeline_id"]

    # step1 result: 10, step2: 30, step3: 31
    assert out["steps"]["step1"]["result"]["result"] == "10"
    assert out["steps"]["step2"]["result"]["result"] == "30"
    assert out["steps"]["step3"]["result"]["result"] == "31"

    from sootool.core.pipeline import resume_pipeline
    resumed = resume_pipeline(pipeline_id, "step2", r)

    # step1 should be reused (not re-executed), step2 and step3 re-executed
    assert resumed["status"] == "ok"
    assert resumed["steps"]["step1"].get("reused") is True
    assert resumed["steps"]["step2"]["result"]["result"] == "30"
    assert resumed["steps"]["step3"]["result"]["result"] == "31"
