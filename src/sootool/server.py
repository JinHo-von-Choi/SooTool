from __future__ import annotations

import json
import os
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from sootool.boundary import SooToolServer, with_error_contract
from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.decimal_ops import add as d_add
from sootool.core.decimal_ops import div as d_div
from sootool.core.decimal_ops import mul as d_mul
from sootool.core.decimal_ops import sub as d_sub
from sootool.core.engines import engine_of
from sootool.core.receipts import sign_stamp
from sootool.core.registry import REGISTRY, ToolEntry
from sootool.core.request_context import STATELESS_REQUEST
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
    session_id: str | None,
    trace_level: str = "summary",
    policy_year: int | None = None,
) -> dict[str, Any]:
    """Record the call in session state and inject _meta.hints into response.

    A ``None`` session means a stateless request: no history is read or recorded and only
    rules that depend on the current call alone can fire.

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
    if session_id is None:
        return inject_meta(response, generate_hints(STORE, None, call), None)

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

    stamp = sign_stamp(
        integrity_stamp(
            tool_name   = tool_name,
            tool_version= tool_version,
            inputs      = _INTEGRITY_CTX.inputs,
            policy_meta = _INTEGRITY_CTX.policy_meta,
            result      = response,
        )
    )

    result = dict(response)
    meta = dict(result.get("_meta", {}))
    meta["integrity"] = stamp
    if entry is not None:
        meta["engine"] = engine_of(entry)
    result["_meta"] = meta
    return result


# ---------------------------------------------------------------------------
# Core tool registration (idempotent — only runs once per process)
# ---------------------------------------------------------------------------

_CORE_TOOLS_REGISTERED = False

# Default session ID for stdio transport (single process, no session header).
_STDIO_SESSION_ID = "stdio-default"


def _get_session_id() -> str | None:
    """Return the current session ID, or None for a stateless request.

    Network transports are stateless (MCP 2026-07-28): their middleware marks every request
    and no call history is kept. stdio and in-process calls share one session for the
    process lifetime.
    """
    return None if STATELESS_REQUEST.get() else _STDIO_SESSION_ID


def _register_core_tools() -> None:
    global _CORE_TOOLS_REGISTERED
    if _CORE_TOOLS_REGISTERED:
        return
    _CORE_TOOLS_REGISTERED = True

    @REGISTRY.tool(namespace="core", name="add", description="Decimal 정밀 덧셈. operands(숫자 문자열 목록)의 합을 result 문자열로 반환하며 float 로 변환하지 않는다.")
    def core_add(operands: list[str], trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.add", formula="sum(operands)")
        decimals = [D(x) for x in operands]
        trace.input("operands", decimals)
        out = d_add(*decimals)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))

    @REGISTRY.tool(namespace="core", name="sub", description="Decimal 정밀 뺄셈 a - b. a 와 b 는 숫자 문자열.")
    def core_sub(a: str, b: str, trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.sub", formula="a-b")
        da, db = D(a), D(b)
        trace.input("a", da)
        trace.input("b", db)
        out = d_sub(da, db)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))

    @REGISTRY.tool(namespace="core", name="mul", description="Decimal 정밀 곱셈. operands(숫자 문자열 목록)의 곱을 result 문자열로 반환한다.")
    def core_mul(operands: list[str], trace_level: str = "summary") -> dict[str, Any]:
        trace = CalcTrace(tool="core.mul", formula="prod(operands)")
        decimals = [D(x) for x in operands]
        trace.input("operands", decimals)
        out = d_mul(*decimals)
        trace.output(out)
        result = {"result": str(out), "trace": trace.to_dict()}
        return _enforce_payload_limit(_apply_trace_level(result, trace_level))

    @REGISTRY.tool(namespace="core", name="div", description="Decimal 정밀 나눗셈 a / b. a 와 b 는 숫자 문자열이며 b 가 0 이면 오류를 반환한다.")
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

    @REGISTRY.tool(namespace="core", name="batch", description="서로 독립인 도구 호출 N개를 병렬 실행한다. 결과는 입력 id 순서로 정렬되며 item_timeout_s 와 batch_timeout_s 가 적용된다.")
    def core_batch(items: list[dict[str, Any]], max_workers: int = 16, item_timeout_s: float = 10.0, batch_timeout_s: float = 60.0, deterministic: bool = True) -> dict[str, Any]:
        ex = BatchExecutor(registry=REGISTRY, max_workers=max_workers, item_timeout_s=item_timeout_s, batch_timeout_s=batch_timeout_s, deterministic=deterministic)
        return ex.run(items=items)

    from sootool.core.pipeline import PipelineExecutor, resume_pipeline

    @REGISTRY.tool(namespace="core", name="pipeline", description="의존 관계(DAG)를 가진 도구 호출을 순서대로 실행하고 앞 단계 결과를 뒤 단계 입력으로 전달한다. step_timeout_s 와 pipeline_timeout_s 가 적용된다.")
    def core_pipeline(steps: list[dict[str, Any]], step_timeout_s: float = 2.0, pipeline_timeout_s: float = 30.0) -> dict[str, Any]:
        ex = PipelineExecutor(registry=REGISTRY, step_timeout_s=step_timeout_s, pipeline_timeout_s=pipeline_timeout_s)
        return ex.run(steps=steps)

    @REGISTRY.tool(namespace="core", name="pipeline_resume", description="이전 core.pipeline 실행을 pipeline_id 로 지정하고 from_step 단계부터 다시 실행한다.")
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
    import sootool.receipt_tools  # noqa: F401
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


def _bind_to_registry(entry: ToolEntry) -> Callable[..., Any]:
    """MCP 노출용 호출자를 만든다.

    REGISTRY.invoke 를 거쳐야 integrity 스탬프와 hints 후처리가 적용된다. 원본 시그니처와 반환
    타입을 유지해 입력·출력 스키마 생성이 그대로 동작하며, 입력 숫자 허용과 오류 계약
    (sootool.boundary)을 함께 적용한다.
    """
    def invoke(**kwargs: Any) -> Any:
        return REGISTRY.invoke(entry.full_name, **kwargs)

    return with_error_contract(entry.fn, invoke)


def _annotations_for(entry: ToolEntry) -> ToolAnnotations:
    """도구 동작 특성을 MCP 어노테이션으로 변환한다.

    계산 도구는 외부 상태를 바꾸지 않는 읽기 전용이다. 정책 쓰기 도구만 readOnlyHint=False 이며
    destructiveHint 로 덮어쓰기 성격을 구분한다. 어노테이션은 클라이언트에 주는 힌트이고 접근
    통제는 admin 게이트가 담당한다.
    """
    if entry.read_only:
        return ToolAnnotations(
            read_only_hint   = True,
            idempotent_hint = entry.idempotent,
            open_world_hint = False,
        )
    return ToolAnnotations(
        read_only_hint   = False,
        destructive_hint= entry.destructive,
        idempotent_hint = entry.idempotent,
        open_world_hint = False,
    )


_LEAN_INSTRUCTIONS = """\
SooTool은 LLM이 직접 계산해서는 안 되는 요청(산수, 세액, 통계, 날짜 차이 등)을
100% 결정론적 Decimal 경로로 대체합니다. 프롬프트 내 직접 산술을 금지합니다.

도구 수가 많아 세 개의 진입 도구만 노출합니다.
1. sootool.search(query)로 도구를 찾는다.
2. sootool.describe(name)로 파라미터를 확인한다.
3. sootool.call(name, arguments)로 실행하고 trace 를 사용자에게 제시한다.
세금·부동산은 year 인자가 필수입니다. sootool.skill_guide()로 활용 가이드를 볼 수 있습니다.
"""

PROFILES = ("full", "lean")
DEFAULT_PROFILE = "full"

# 도구 목록은 프로세스 수명 동안 바뀌지 않고 모든 인증 맥락에서 같으므로 공유 캐시를 허용한다.
TOOLS_LIST_TTL_MS = 3_600_000
_CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=TOOLS_LIST_TTL_MS, scope="public"),
}


def _add_registry_tool(server: MCPServer, entry: ToolEntry) -> None:
    server.add_tool(
        _bind_to_registry(entry),
        name        = entry.full_name,
        description = entry.description,
        annotations = _annotations_for(entry),
    )


def build_server(profile: str = DEFAULT_PROFILE, *, expose_writes: bool = True) -> MCPServer:
    """프로파일에 따라 노출 도구를 구성한 서버를 만든다.

    full: 등록된 모든 도구를 노출한다.
    lean: 검색·설명·호출 파사드 3종과 skill_guide 만 노출해 컨텍스트 비용을 줄인다.

    expose_writes=False 이면 읽기 전용이 아닌 도구(정책 쓰기)를 노출하지 않는다. 네트워크 전송용
    서버가 쓰기 도구를 아예 광고하지 않게 하는 구성이다.
    """
    if profile not in PROFILES:
        raise ValueError(f"알 수 없는 프로파일: {profile!r} (허용: {', '.join(PROFILES)})")

    if profile == "full":
        server = SooToolServer("sootool", instructions=_SOOTOOL_INSTRUCTIONS, cache_hints=_CACHE_HINTS)
        # 결정적 순서(이름 오름차순): 클라이언트 캐시와 프롬프트 캐시 적중률을 위해 등록 순서와 무관하게 고정한다.
        for entry in sorted(REGISTRY.list(), key=lambda e: e.full_name):
            if entry.read_only or expose_writes:
                _add_registry_tool(server, entry)
        return server

    from sootool.facade import register_facade  # noqa: PLC0415

    server = SooToolServer("sootool", instructions=_LEAN_INSTRUCTIONS, cache_hints=_CACHE_HINTS)
    register_facade(server)
    for entry in REGISTRY.list():
        if entry.full_name == "sootool.skill_guide":
            _add_registry_tool(server, entry)
    return server


def invoke_tool(full_name: str, args: dict[str, Any]) -> Any:
    """Direct invocation for testing — bypasses FastMCP transport."""
    return REGISTRY.invoke(full_name, **args)
