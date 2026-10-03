"""MCP 에 의존하지 않는 실행 기반: 핵심 도구 등록, 후처리(힌트, 영수증), 도메인 모듈 로드.

MCP 서버(``sootool.server``)와 라이브러리 사용(``sootool.sdk``)이 같은 경로를 쓰도록 분리했다. 이 모듈은
mcp 패키지를 가져오지 않으므로 가져오는 비용이 작다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any, NotRequired, cast

from sootool.core.audit import CalcTrace
from sootool.core.batch import BatchExecutor, BatchResult
from sootool.core.calc import calc as _calc
from sootool.core.calc.api import CalcResult
from sootool.core.decimal_ops import D
from sootool.core.decimal_ops import add as d_add
from sootool.core.decimal_ops import div as d_div
from sootool.core.decimal_ops import mul as d_mul
from sootool.core.decimal_ops import sub as d_sub
from sootool.core.engines import engine_of
from sootool.core.pipeline import PipelineExecutor, PipelineResult, resume_pipeline
from sootool.core.receipts import sign_stamp
from sootool.core.registry import REGISTRY
from sootool.core.request_context import STATELESS_REQUEST
from sootool.core.result_types import ToolResult, Trace
from sootool.skill_guide.hints import generate_hints, inject_meta
from sootool.skill_guide.session_state import STORE, ToolCall

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class ArithmeticResult(ToolResult):
    """core.add, sub, mul, div 의 결과. trace_level=none 이거나 응답 크기 한도로 잘리면 trace 가 없다."""

    result:    str
    trace:     NotRequired[Trace]
    truncated: NotRequired[bool]


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
            # Still over, strip trace entirely
            result.pop("trace", None)

    result["truncated"] = True
    return result


def _arithmetic_response(out: Decimal, trace: CalcTrace, trace_level: str) -> ArithmeticResult:
    """사칙연산 결과를 trace 수준과 응답 크기 한도에 맞춰 응답으로 만든다."""
    trace.output(out)
    result = {"result": str(out), "trace": trace.to_dict()}
    return cast(ArithmeticResult, _enforce_payload_limit(_apply_trace_level(result, trace_level)))


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
    ``policy_mgmt.loader.load``. Result and trace fields are never modified ,
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
        if entry.deprecated:
            meta["deprecated"] = dict(entry.deprecated)
    result["_meta"] = meta
    return result


# ---------------------------------------------------------------------------
# Core tool registration (idempotent, only runs once per process)
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

    @REGISTRY.tool(namespace="core", name="add", description="Decimal 정밀 덧셈. operands(쉼표, 단위, 공백 없는 숫자 문자열 목록)의 합을 result 문자열로 반환한다. 유효숫자 50자리 안에서 계산하고 별도 반올림은 없다. trace_level 은 summary(기본), full, none. 합계를 직접 암산하지 말고 이 도구로 구한다.")
    def core_add(operands: list[str], trace_level: str = "summary") -> ArithmeticResult:
        trace = CalcTrace(tool="core.add", formula="sum(operands)")
        decimals = [D(x) for x in operands]
        trace.input("operands", decimals)
        return _arithmetic_response(d_add(*decimals), trace, trace_level)

    @REGISTRY.tool(namespace="core", name="sub", description="Decimal 정밀 뺄셈 a - b. a 와 b 는 쉼표, 단위, 공백 없는 숫자 문자열이며 결과는 result 문자열이다. 유효숫자 50자리 안에서 계산하고 별도 반올림은 없다. 순서에 주의한다(a 에서 b 를 뺀다).")
    def core_sub(a: str, b: str, trace_level: str = "summary") -> ArithmeticResult:
        trace = CalcTrace(tool="core.sub", formula="a-b")
        da, db = D(a), D(b)
        trace.input("a", da)
        trace.input("b", db)
        return _arithmetic_response(d_sub(da, db), trace, trace_level)

    @REGISTRY.tool(namespace="core", name="mul", description="Decimal 정밀 곱셈. operands(쉼표, 단위, 공백 없는 숫자 문자열 목록)의 곱을 result 문자열로 반환한다. 유효숫자 50자리를 넘는 곱은 그 자릿수로 반올림되며 그 밖의 반올림은 없다. 세금이나 이자 계산에는 전용 도구를 쓴다.")
    def core_mul(operands: list[str], trace_level: str = "summary") -> ArithmeticResult:
        trace = CalcTrace(tool="core.mul", formula="prod(operands)")
        decimals = [D(x) for x in operands]
        trace.input("operands", decimals)
        return _arithmetic_response(d_mul(*decimals), trace, trace_level)

    @REGISTRY.tool(namespace="core", name="div", description="Decimal 정밀 나눗셈 a / b. a 와 b 는 쉼표, 단위, 공백 없는 숫자 문자열이며 b 가 0 이면 오류를 반환한다. 몫은 유효숫자 50자리로 계산되어 나누어떨어지지 않으면 50자리에서 끊긴다. 정수 몫이나 원 단위 절사가 필요하면 결과를 별도로 반올림한다.")
    def core_div(a: str, b: str, trace_level: str = "summary") -> ArithmeticResult:
        trace = CalcTrace(tool="core.div", formula="a/b")
        da, db = D(a), D(b)
        trace.input("a", da)
        trace.input("b", db)
        return _arithmetic_response(d_div(da, db), trace, trace_level)

    @REGISTRY.tool(namespace="core", name="batch", description="서로 독립인 도구 호출 N개를 병렬 실행한다. items 는 id, tool, args 를 가진 객체 목록(최대 500개, id 중복 불가)이고 읽기 전용 도구만 실행된다. 결과는 입력 id 순서이며 항목별 status(ok, error, timeout)와 item_timeout_s, batch_timeout_s 가 적용된다. 앞 결과를 뒤 입력에 쓰려면 core.pipeline 을 쓴다.")
    def core_batch(items: list[dict[str, Any]], max_workers: int = 16, item_timeout_s: float = 10.0, batch_timeout_s: float = 60.0, deterministic: bool = True) -> BatchResult:
        ex = BatchExecutor(registry=REGISTRY, max_workers=max_workers, item_timeout_s=item_timeout_s, batch_timeout_s=batch_timeout_s, deterministic=deterministic)
        return ex.run(items=items)

    @REGISTRY.tool(namespace="core", name="pipeline", description="의존 관계(DAG)를 가진 도구 호출을 순서대로 실행하고 앞 단계 결과를 뒤 단계 입력으로 전달한다. steps 는 id, tool, args 목록(최대 50단계, 깊이 10)이며 args 에서 ${단계id.result.필드} 로 앞 결과를 참조한다. 실패한 단계의 하류는 skipped 가 되고 pipeline_id 로 재개할 수 있다. 서로 독립인 호출은 core.batch 를 쓴다.")
    def core_pipeline(steps: list[dict[str, Any]], step_timeout_s: float = 2.0, pipeline_timeout_s: float = 30.0) -> PipelineResult:
        ex = PipelineExecutor(registry=REGISTRY, step_timeout_s=step_timeout_s, pipeline_timeout_s=pipeline_timeout_s)
        return ex.run(steps=steps)

    @REGISTRY.tool(namespace="core", name="pipeline_resume", description="이전 core.pipeline 실행을 pipeline_id 로 지정하고 from_step 단계부터 다시 실행한다. from_step 앞쪽의 성공 단계는 결과를 재사용(reused)한다. 실행 기록은 약 10분 동안만 보관되어 만료되면 오류가 난다. 입력을 바꿔 다시 계산하려면 새로 core.pipeline 을 호출한다.")
    def core_pipeline_resume(pipeline_id: str, from_step: str) -> PipelineResult:
        return resume_pipeline(pipeline_id, from_step, REGISTRY)

    @REGISTRY.tool(
        namespace   = "core",
        name        = "calc",
        description = (
            "AST 기반 안전 수식 평가기. expression 은 사칙, %, //, **, 괄호, 함수(sqrt, abs, floor, ceil, round, log, ln, exp, 삼각함수 등), "
            "상수(pi, e, tau)를 쓸 수 있고 variables 는 Decimal 문자열 전용이다. 결과는 precision(기본 50)자리 십진 문자열이다. "
            "비교, 조건식, 속성 접근은 거부한다. 세금, 금융 공식은 전용 도구를 쓴다."
        ),
        version     = "1.0.0",
    )
    def core_calc(
        expression:  str,
        variables:   dict[str, str] | None = None,
        precision:   int                   = 50,
        trace_level: str                   = "summary",
    ) -> CalcResult:
        result = _calc(
            expression  = expression,
            variables   = variables,
            precision   = precision,
            trace_level = trace_level,
        )
        return cast(CalcResult, _enforce_payload_limit(_apply_trace_level(result, trace_level)))



_register_core_tools()
REGISTRY.register_post_processor(_hints_post_processor)
REGISTRY.register_post_processor(_integrity_post_processor)


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

# 네임스페이스를 등록하는 모듈. 가져오면 해당 도구가 REGISTRY 에 등록된다.
NAMESPACE_MODULES: dict[str, tuple[str, ...]] = {
    "accounting":  ("sootool.modules.accounting",),
    "core":        ("sootool.core.analysis_tools",),
    "crypto":      ("sootool.modules.crypto",),
    "datetime":    ("sootool.modules.datetime_",),
    "engineering": ("sootool.modules.engineering",),
    "finance":     ("sootool.modules.finance",),
    "geometry":    ("sootool.modules.geometry",),
    "math":        ("sootool.modules.math",),
    "medical":     ("sootool.modules.medical",),
    "payroll":     ("sootool.modules.payroll",),
    "pm":          ("sootool.modules.pm",),
    "probability": ("sootool.modules.probability",),
    "realestate":  ("sootool.modules.realestate",),
    "science":     ("sootool.modules.science",),
    "sootool":     ("sootool.policy_mgmt.tools", "sootool.receipt_tools", "sootool.skill_guide"),
    "stats":       ("sootool.modules.stats",),
    "symbolic":    ("sootool.modules.symbolic",),  # 선택 extra: pip install 'sootool[symbolic]'
    "tax":         ("sootool.modules.tax",),
    "tax_us":      ("sootool.modules.tax_us",),
    "units":       ("sootool.modules.units",),
}
_OPTIONAL_NAMESPACES = frozenset({"symbolic"})


def load_namespace(namespace: str) -> None:
    """네임스페이스 하나의 도구를 등록한다. 알 수 없는 이름이면 KeyError."""
    import importlib

    for module in NAMESPACE_MODULES[namespace]:
        importlib.import_module(module)


def _load_modules() -> None:
    """모든 도구 모듈을 가져와 REGISTRY 에 등록한다."""
    for namespace in NAMESPACE_MODULES:
        try:
            load_namespace(namespace)
        except ImportError:
            if namespace not in _OPTIONAL_NAMESPACES:
                raise
