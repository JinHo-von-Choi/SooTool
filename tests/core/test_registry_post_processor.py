"""Tests for ToolRegistry.register_post_processor() and REGISTRY.invoke() chain."""
from __future__ import annotations

from typing import Any

from sootool.core.registry import ToolRegistry


def _make_registry_with_tool() -> tuple[ToolRegistry, list[str]]:
    """Return a fresh registry with one tool and a call-order log."""
    r = ToolRegistry()

    @r.tool(namespace="t", name="op", description="test op")
    def _op(x: int) -> dict[str, Any]:
        return {"result": x * 2, "trace": {"tool": "t.op"}}

    return r, []


class TestPostProcessorRegistration:
    def test_no_processor_returns_raw(self) -> None:
        r, _ = _make_registry_with_tool()
        result = r.invoke("t.op", x=3)
        assert result == {"result": 6, "trace": {"tool": "t.op"}}

    def test_single_processor_applied(self) -> None:
        r, _ = _make_registry_with_tool()

        def proc(resp: dict[str, Any], name: str) -> dict[str, Any]:
            resp = dict(resp)
            resp["_meta"] = {"processed_by": name}
            return resp

        r.register_post_processor(proc)
        result = r.invoke("t.op", x=5)
        assert "_meta" in result
        assert result["_meta"]["processed_by"] == "t.op"

    def test_multiple_processors_applied_in_order(self) -> None:
        r, _ = _make_registry_with_tool()
        order: list[str] = []

        def proc_a(resp: dict[str, Any], name: str) -> dict[str, Any]:
            order.append("a")
            resp = dict(resp)
            resp.setdefault("_meta", {})["a"] = True
            return resp

        def proc_b(resp: dict[str, Any], name: str) -> dict[str, Any]:
            order.append("b")
            resp = dict(resp)
            resp.setdefault("_meta", {})["b"] = True
            return resp

        r.register_post_processor(proc_a)
        r.register_post_processor(proc_b)
        result = r.invoke("t.op", x=1)
        assert order == ["a", "b"]
        assert result["_meta"]["a"] is True
        assert result["_meta"]["b"] is True

    def test_processor_exception_returns_original(self) -> None:
        """A failing post-processor must not propagate; original result is returned."""
        r, _ = _make_registry_with_tool()

        def bad_proc(resp: dict[str, Any], name: str) -> dict[str, Any]:
            raise RuntimeError("processor failure")

        r.register_post_processor(bad_proc)
        result = r.invoke("t.op", x=7)
        assert result["result"] == 14
        assert "_meta" not in result


class TestPostProcessorOnlyForTraceDicts:
    def test_non_dict_result_skips_processors(self) -> None:
        r = ToolRegistry()
        called: list[bool] = []

        @r.tool(namespace="t", name="raw")
        def _raw() -> int:
            return 42

        def proc(resp: dict[str, Any], name: str) -> dict[str, Any]:
            called.append(True)
            return resp

        r.register_post_processor(proc)
        result = r.invoke("t.raw")
        assert result == 42
        assert called == []

    def test_dict_without_trace_skips_processors(self) -> None:
        r = ToolRegistry()
        called: list[bool] = []

        @r.tool(namespace="t", name="notrace")
        def _notrace() -> dict[str, Any]:
            return {"result": "ok"}

        def proc(resp: dict[str, Any], name: str) -> dict[str, Any]:
            called.append(True)
            return resp

        r.register_post_processor(proc)
        result = r.invoke("t.notrace")
        assert result == {"result": "ok"}
        assert called == []

    def test_dict_with_trace_triggers_processors(self) -> None:
        r = ToolRegistry()
        called: list[str] = []

        @r.tool(namespace="t", name="withtrace")
        def _wt() -> dict[str, Any]:
            return {"result": "x", "trace": {"tool": "t.withtrace"}}

        def proc(resp: dict[str, Any], name: str) -> dict[str, Any]:
            called.append(name)
            return resp

        r.register_post_processor(proc)
        r.invoke("t.withtrace")
        assert called == ["t.withtrace"]


class TestMetaStructure:
    def test_meta_key_written_to_response(self) -> None:
        r = ToolRegistry()

        @r.tool(namespace="t", name="m")
        def _m() -> dict[str, Any]:
            return {"result": "1", "trace": {"tool": "t.m"}}

        def proc(resp: dict[str, Any], name: str) -> dict[str, Any]:
            out = dict(resp)
            out["_meta"] = {"hints": [], "session_stats": {"tool_calls": 1, "unique_tools": 1}}
            return out

        r.register_post_processor(proc)
        result = r.invoke("t.m")
        assert "_meta" in result
        assert "hints" in result["_meta"]
        assert "session_stats" in result["_meta"]
        # result and trace unchanged
        assert result["result"] == "1"
        assert result["trace"]["tool"] == "t.m"
