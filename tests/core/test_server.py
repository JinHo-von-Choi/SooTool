from __future__ import annotations

from decimal import Decimal


def test_server_exposes_core_add():
    import sootool.server  # noqa: F401 — triggers _register_core_tools() side-effect
    from sootool.core.registry import REGISTRY
    names = {e.full_name for e in REGISTRY.list()}
    assert "core.add" in names
    assert "core.mul" in names


def test_server_invokes_core_add():
    from sootool.server import invoke_tool
    result = invoke_tool("core.add", {"operands": ["1.1", "2.2", "3.3"]})
    assert result["result"] == "6.6"
    assert result["trace"]["tool"] == "core.add"


def test_build_server_returns_fastmcp():
    from mcp.server.fastmcp import FastMCP

    from sootool.server import build_server
    server = build_server()
    assert isinstance(server, FastMCP)


def test_registry_has_core_arithmetic():
    from sootool.core.registry import REGISTRY
    names = {e.full_name for e in REGISTRY.list()}
    for expected in ("core.add", "core.sub", "core.mul", "core.div"):
        assert expected in names, f"Missing: {expected}"


# --- _parse_request_json ---

def test_parse_request_json_preserves_decimal():
    from sootool.server import _parse_request_json
    result = _parse_request_json('{"x": 0.1}')
    assert isinstance(result["x"], Decimal), f"Expected Decimal, got {type(result['x'])}"
    assert result["x"] == Decimal("0.1")


def test_parse_request_json_integer_unaffected():
    from sootool.server import _parse_request_json
    result = _parse_request_json('{"n": 42}')
    assert result["n"] == 42


# --- _apply_trace_level ---

def test_trace_level_none_strips_trace():
    from sootool.server import _apply_trace_level, invoke_tool
    result = invoke_tool("core.add", {"operands": ["1", "2"]})
    result = _apply_trace_level(result, "none")
    assert "trace" not in result


def test_trace_level_summary_default():
    from sootool.server import _apply_trace_level, invoke_tool
    result = invoke_tool("core.add", {"operands": ["1", "2"]})
    result = _apply_trace_level(result, "summary")
    trace = result["trace"]
    assert "steps" not in trace
    for key in ("tool", "formula", "inputs", "output"):
        assert key in trace, f"Missing key in summary trace: {key}"


def test_trace_level_full_keeps_steps():
    from sootool.server import _apply_trace_level, invoke_tool
    result = invoke_tool("core.add", {"operands": ["1", "2"]})
    # Inject a step manually to verify full preserves it
    result["trace"]["steps"] = [{"label": "test_step", "value": "x"}]
    result = _apply_trace_level(result, "full")
    assert "steps" in result["trace"]
    assert result["trace"]["steps"] == [{"label": "test_step", "value": "x"}]


# --- _enforce_payload_limit ---

def test_payload_limit_truncates(monkeypatch):
    import json

    from sootool.server import _enforce_payload_limit
    monkeypatch.setenv("SOOTOOL_MAX_PAYLOAD_KB", "1")

    # Build a response whose trace.steps are large
    big_steps = [{"label": f"step_{i}", "value": "x" * 100} for i in range(50)]
    response = {
        "result": "42",
        "trace": {
            "tool": "core.test",
            "formula": "test",
            "inputs": {},
            "output": "42",
            "steps": big_steps,
        },
    }

    # Verify it is over 1 KB before the call
    raw_size = len(json.dumps(response, default=str).encode("utf-8"))
    assert raw_size > 1024, f"Pre-condition failed: response is only {raw_size} bytes"

    result = _enforce_payload_limit(response)
    assert result.get("truncated") is True


def test_payload_limit_no_truncation_when_small():
    from sootool.server import _enforce_payload_limit, invoke_tool
    result = invoke_tool("core.add", {"operands": ["1", "2"]})
    # Default 512 KB limit — a tiny result must not be flagged
    result = _enforce_payload_limit(result)
    assert result.get("truncated") is not True


def test_server_core_batch_roundtrip():
    from sootool.server import invoke_tool
    out = invoke_tool("core.batch", {
        "items": [
            {"id": "x", "tool": "core.add", "args": {"operands": ["1", "2", "3"]}},
            {"id": "y", "tool": "core.mul", "args": {"operands": ["2", "3", "4"]}},
        ]
    })
    assert out["status"] == "all_ok"
    by_id = {r["id"]: r for r in out["results"]}
    assert by_id["x"]["result"]["result"] == "6"
    assert by_id["y"]["result"]["result"] == "24"


def test_server_core_pipeline_chain():
    from sootool.server import invoke_tool
    out = invoke_tool("core.pipeline", {
        "steps": [
            {"id": "sum", "tool": "core.add", "args": {"operands": ["1", "2", "3"]}},
            {"id": "double", "tool": "core.mul", "args": {"operands": ["${sum.result.result}", "2"]}},
        ]
    })
    assert out["status"] == "ok"
    assert out["steps"]["double"]["result"]["result"] == "12"
