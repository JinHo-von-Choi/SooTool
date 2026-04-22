from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add as d_add, div as d_div, mul as d_mul, sub as d_sub
from sootool.core.registry import REGISTRY


# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------

def _parse_request_json(raw: str) -> dict:
    """Parse JSON string using Decimal for float values."""
    return json.loads(raw, parse_float=Decimal)


# ---------------------------------------------------------------------------
# Trace level filtering
# ---------------------------------------------------------------------------

_SUMMARY_KEYS = {"tool", "formula", "inputs", "output"}


def _apply_trace_level(response: dict, level: str = "summary") -> dict:
    """Filter trace content based on requested verbosity level.

    - none:    remove trace entirely
    - summary: keep only tool/formula/inputs/output; strip steps
    - full:    return trace unchanged
    """
    result = dict(response)

    if level == "none":
        result.pop("trace", None)
        return result

    if level == "full":
        return result

    # summary (default)
    if "trace" in result:
        trace = dict(result["trace"])
        result["trace"] = {k: v for k, v in trace.items() if k in _SUMMARY_KEYS}

    return result


# ---------------------------------------------------------------------------
# Payload size guard
# ---------------------------------------------------------------------------

def _enforce_payload_limit(response: dict) -> dict:
    """Truncate trace.steps from tail if response exceeds SOOTOOL_MAX_PAYLOAD_KB.

    If still over limit after stripping all steps, removes trace entirely and
    sets response["truncated"] = True.
    """
    limit_kb = int(os.environ.get("SOOTOOL_MAX_PAYLOAD_KB", "512"))
    limit_bytes = limit_kb * 1024

    def _size(d: dict) -> int:
        return len(json.dumps(d, default=str).encode("utf-8"))

    if _size(response) <= limit_bytes:
        return response

    result = {k: (dict(v) if isinstance(v, dict) else v) for k, v in response.items()}
    if "trace" in result and isinstance(result["trace"], dict):
        result["trace"] = dict(result["trace"])

    # Trim steps from tail one at a time
    if "trace" in result and "steps" in result["trace"]:
        steps = list(result["trace"]["steps"])
        while steps and _size(result) > limit_bytes:
            steps.pop()
            result["trace"]["steps"] = steps
        if _size(result) > limit_bytes:
            # Still over — strip trace entirely
            result.pop("trace", None)

    result["truncated"] = True
    return result


# ---------------------------------------------------------------------------
# Core tool registration (idempotent — only runs once per process)
# ---------------------------------------------------------------------------

_CORE_TOOLS_REGISTERED = False


def _register_core_tools() -> None:
    global _CORE_TOOLS_REGISTERED
    if _CORE_TOOLS_REGISTERED:
        return
    _CORE_TOOLS_REGISTERED = True

    @REGISTRY.tool(namespace="core", name="add", description="Decimal 가감산(정밀)")
    def core_add(operands: list[str], trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.add", formula="sum(operands)")
        decimals = [D(x) for x in operands]
        trace.input("operands", decimals)
        out = d_add(*decimals)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))

    @REGISTRY.tool(namespace="core", name="sub", description="Decimal 뺄셈")
    def core_sub(a: str, b: str, trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.sub", formula="a-b")
        da, db = D(a), D(b)
        trace.input("a", da)
        trace.input("b", db)
        out = d_sub(da, db)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))

    @REGISTRY.tool(namespace="core", name="mul", description="Decimal 곱셈")
    def core_mul(operands: list[str], trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.mul", formula="prod(operands)")
        decimals = [D(x) for x in operands]
        trace.input("operands", decimals)
        out = d_mul(*decimals)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))

    @REGISTRY.tool(namespace="core", name="div", description="Decimal 나눗셈(분모 0 예외)")
    def core_div(a: str, b: str, trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.div", formula="a/b")
        da, db = D(a), D(b)
        trace.input("a", da)
        trace.input("b", db)
        out = d_div(da, db)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))


_register_core_tools()


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def _load_modules() -> None:
    """Phase 1+ modules activate here when ready."""
    pass


def build_server() -> FastMCP:
    server = FastMCP("sootool")
    for entry in REGISTRY.list():
        server.add_tool(entry.fn, name=entry.full_name, description=entry.description)
    return server


def invoke_tool(full_name: str, args: dict[str, Any]) -> Any:
    """Direct invocation for testing — bypasses FastMCP transport."""
    return REGISTRY.invoke(full_name, **args)
