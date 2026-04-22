from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.decimal_ops import add as d_add
from sootool.core.decimal_ops import div as d_div
from sootool.core.decimal_ops import mul as d_mul
from sootool.core.decimal_ops import sub as d_sub
from sootool.core.registry import REGISTRY

# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------

def _parse_request_json(raw: str) -> dict[str, Any]:
    """Parse JSON string using Decimal for float values."""
    return json.loads(raw, parse_float=Decimal)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Trace level filtering
# ---------------------------------------------------------------------------

_SUMMARY_KEYS = {"tool", "formula", "inputs", "output"}


def _apply_trace_level(response: dict[str, Any], level: str = "summary") -> dict[str, Any]:
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

def _enforce_payload_limit(response: dict[str, Any]) -> dict[str, Any]:
    """Truncate trace.steps from tail if response exceeds SOOTOOL_MAX_PAYLOAD_KB.

    If still over limit after stripping all steps, removes trace entirely and
    sets response["truncated"] = True.
    """
    limit_kb = int(os.environ.get("SOOTOOL_MAX_PAYLOAD_KB", "512"))
    limit_bytes = limit_kb * 1024

    def _size(d: dict[str, Any]) -> int:
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

    from sootool.core.batch import BatchExecutor  # noqa: PLC0415

    @REGISTRY.tool(namespace="core", name="batch", description="독립 연산 N개 병렬 실행")
    def core_batch(items: list[dict[str, Any]], max_workers: int = 16, item_timeout_s: float = 10.0, batch_timeout_s: float = 60.0, deterministic: bool = True) -> dict[str, Any]:
        ex = BatchExecutor(registry=REGISTRY, max_workers=max_workers, item_timeout_s=item_timeout_s, batch_timeout_s=batch_timeout_s, deterministic=deterministic)
        return ex.run(items=items)

    from sootool.core.pipeline import PipelineExecutor, resume_pipeline

    @REGISTRY.tool(namespace="core", name="pipeline", description="DAG 의존 연산")
    def core_pipeline(steps: list[dict[str, Any]], step_timeout_s: float = 2.0, pipeline_timeout_s: float = 30.0) -> dict[str, Any]:
        ex = PipelineExecutor(registry=REGISTRY, step_timeout_s=step_timeout_s, pipeline_timeout_s=pipeline_timeout_s)
        return ex.run(steps=steps)

    @REGISTRY.tool(namespace="core", name="pipeline_resume", description="파이프라인 부분 재실행")
    def core_pipeline_resume(pipeline_id: str, from_step: str) -> dict[str, Any]:
        return resume_pipeline(pipeline_id, from_step, REGISTRY)


_register_core_tools()


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def _load_modules() -> None:
    """Import Phase 1+ modules to trigger REGISTRY auto-registration."""
    import sootool.modules.accounting  # noqa: F401
    import sootool.modules.crypto  # noqa: F401
    import sootool.modules.datetime_  # noqa: F401
    import sootool.modules.engineering  # noqa: F401
    import sootool.modules.finance  # noqa: F401
    import sootool.modules.geometry  # noqa: F401
    import sootool.modules.medical  # noqa: F401
    import sootool.modules.pm  # noqa: F401
    import sootool.modules.probability  # noqa: F401
    import sootool.modules.realestate  # noqa: F401
    import sootool.modules.science  # noqa: F401
    import sootool.modules.stats  # noqa: F401
    import sootool.modules.tax  # noqa: F401
    import sootool.modules.units  # noqa: F401


def build_server() -> FastMCP:
    server = FastMCP("sootool")
    for entry in REGISTRY.list():
        server.add_tool(entry.fn, name=entry.full_name, description=entry.description)
    return server


def invoke_tool(full_name: str, args: dict[str, Any]) -> Any:
    """Direct invocation for testing — bypasses FastMCP transport."""
    return REGISTRY.invoke(full_name, **args)
