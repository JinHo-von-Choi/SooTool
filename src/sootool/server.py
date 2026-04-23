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
from sootool.skill_guide.hints import generate_hints, inject_meta
from sootool.skill_guide.session_state import STORE, ToolCall

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
# _meta.hints injection pipeline
# ---------------------------------------------------------------------------

def _inject_hints(
    response: dict[str, Any],
    tool_name: str,
    session_id: str,
    trace_level: str = "summary",
    policy_year: int | None = None,
) -> dict[str, Any]:
    """Record the call in session state and inject _meta.hints into response.

    result and trace are never modified (ADR-011 determinism guard).
    Skipped for sootool.skill_guide itself to avoid recursive noise.
    """
    truncated = bool(response.get("truncated", False))

    call = ToolCall(
        tool=tool_name,
        trace_level=trace_level,
        truncated=truncated,
        policy_year=policy_year,
    )
    STORE.record(session_id, call)

    hints      = generate_hints(STORE, session_id, call)
    stats      = STORE.stats(session_id)
    return inject_meta(response, hints, stats)


def _hints_post_processor(response: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Post-processor adapter for REGISTRY.register_post_processor().

    Skips sootool.skill_guide to avoid recursive noise.
    Already-injected _meta (from domain tools that call _inject_hints directly)
    is left untouched; this processor only runs when _meta is absent.
    """
    if tool_name == "sootool.skill_guide":
        return response
    if "_meta" in response:
        return response
    return _inject_hints(response, tool_name, _get_session_id())



def _integrity_post_processor(response: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Inject a deterministic reproducibility stamp into ``_meta.integrity``.

    Reads the in-flight tool kwargs and (optional) policy metadata from the
    thread-local integrity context populated by ``REGISTRY.invoke`` and
    ``policy_mgmt.loader.load``. Result and trace fields are never modified —
    only ``_meta.integrity`` is added (ADR-011 / ADR-021 invariant).

    ``sootool.skill_guide`` is skipped to keep the guide output minimal.
    """
    if tool_name == "sootool.skill_guide":
        return response

    from sootool.core.audit import _INTEGRITY_CTX, integrity_stamp
    from sootool.core.registry import REGISTRY as _REG

    entry = _REG._tools.get(tool_name)
    tool_version = entry.version if entry is not None else "0.0.0"

    stamp = integrity_stamp(
        tool_name   = tool_name,
        tool_version= tool_version,
        inputs      = _INTEGRITY_CTX.inputs,
        policy_meta = _INTEGRITY_CTX.policy_meta,
    )

    result = dict(response)
    meta = dict(result.get("_meta", {}))
    meta["integrity"] = stamp
    result["_meta"] = meta
    return result


# ---------------------------------------------------------------------------
# Core tool registration (idempotent — only runs once per process)
# ---------------------------------------------------------------------------

_CORE_TOOLS_REGISTERED = False

# Default session ID for stdio transport (single process, no session header).
_STDIO_SESSION_ID = "stdio-default"


def _get_session_id() -> str:
    """Return the current session ID.

    HTTP transport sets SOOTOOL_SESSION_ID via middleware (future M3+).
    stdio uses a fixed constant for the process lifetime.
    """
    return os.environ.get("SOOTOOL_SESSION_ID", _STDIO_SESSION_ID)


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

    from sootool.core.calc import calc as _calc  # noqa: PLC0415

    @REGISTRY.tool(
        namespace   = "core",
        name        = "calc",
        description = (
            "AST 기반 안전 수식 평가기. Decimal 결과 + mpmath 초월 함수. "
            "변수 바인딩 Decimal 문자열 전용."
        ),
        version     = "1.0.0",
    )
    def core_calc(
        expression:  str,
        variables:   dict[str, str] | None = None,
        precision:   int                   = 50,
        trace_level: str                   = "summary",
    ) -> dict[str, Any]:
        result = _calc(
            expression  = expression,
            variables   = variables,
            precision   = precision,
            trace_level = trace_level,
        )
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))



_register_core_tools()
REGISTRY.register_post_processor(_hints_post_processor)
REGISTRY.register_post_processor(_integrity_post_processor)


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
    import sootool.modules.math  # noqa: F401
    import sootool.modules.medical  # noqa: F401
    import sootool.modules.payroll  # noqa: F401
    import sootool.modules.pm  # noqa: F401
    import sootool.modules.probability  # noqa: F401
    import sootool.modules.realestate  # noqa: F401
    import sootool.modules.science  # noqa: F401
    import sootool.modules.stats  # noqa: F401
    try:
        import sootool.modules.symbolic  # noqa: F401
    except ImportError:
        pass  # optional extra: pip install 'sootool[symbolic]'
    import sootool.modules.tax  # noqa: F401
    import sootool.modules.tax_us  # noqa: F401
    import sootool.modules.units  # noqa: F401
    import sootool.policy_mgmt.tools  # noqa: F401
    import sootool.skill_guide  # noqa: F401


_SOOTOOL_INSTRUCTIONS = """\
SooTool은 LLM이 직접 계산해서는 안 되는 요청(산수, 세액, 할인율, 통계, 날짜 차이 등)을
100% 결정론적 Decimal 경로로 대체합니다.

세션 시작 시 sootool.skill_guide()를 호출해 트리거 테이블을 숙지하세요.
수치 계산이 포함된 응답에서는 사전에 해당 도메인 도구를 호출하고 trace를 사용자에게
제시하세요. 프롬프트 내 직접 산술을 금지합니다.

핵심 원칙:
- 숫자 연산은 core.add/sub/mul/div 또는 core.batch/pipeline으로 처리
- 세금·부동산은 tax.* / realestate.* (year 인자 필수)
- 금융 계산은 finance.* (Decimal 복리 정확도)
- 통계는 stats.* / probability.* (scipy/mpmath 기반)
- 복수 시나리오는 core.batch, 결과 체이닝은 core.pipeline
"""


def build_server() -> FastMCP:
    server = FastMCP("sootool", instructions=_SOOTOOL_INSTRUCTIONS)
    for entry in REGISTRY.list():
        server.add_tool(entry.fn, name=entry.full_name, description=entry.description)
    return server


def invoke_tool(full_name: str, args: dict[str, Any]) -> Any:
    """Direct invocation for testing — bypasses FastMCP transport."""
    return REGISTRY.invoke(full_name, **args)
