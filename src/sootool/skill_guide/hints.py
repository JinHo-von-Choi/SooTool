"""_meta.hints generation rules.

Six rules derived from session call history. Result/trace are never modified;
hints are injected only into _meta to preserve determinism (ADR-011).
"""
from __future__ import annotations

import datetime
from typing import Any

from sootool.skill_guide.session_state import InMemoryStore, ToolCall

_CURRENT_YEAR = datetime.date.today().year

# Domains that are tax-related
_TAX_DOMAINS = {"tax", "realestate"}
# Core arithmetic tools
_CORE_ARITH = {"core.add", "core.sub", "core.mul", "core.div"}


def generate_hints(
    store: InMemoryStore,
    session_id: str,
    current_call: ToolCall,
) -> list[dict[str, Any]]:
    """Generate hints based on session call history and current call.

    Rules (plan §3._meta.hints):
    1. tax.* + trace_level != full -> audit warning
    2. core arithmetic 3+ consecutive -> suggest core.batch
    3. policy year older than current year -> refresh warning
    4. trace truncated -> payload limit hint
    5. manual chain detected (prev result likely fed as input) -> suggest core.pipeline
    6. 20+ single calls without core.batch -> round-trip warning
    """
    hints: list[dict[str, Any]] = []
    history = store.recent(session_id)

    # Rule 1: tax domain + non-full trace
    if current_call.domain in _TAX_DOMAINS and current_call.trace_level != "full":
        hints.append({
            "signal":           "tax_without_full_trace",
            "suggestion":       "감사 대비 trace_level=full 권장. 세무·회계 계산은 전체 audit trail 보존이 법적 요건일 수 있습니다.",
            "recommended_tool": None,
        })

    # Rule 2: core arithmetic 3+ consecutive
    recent_arith = _count_trailing_arith(history)
    if current_call.tool in _CORE_ARITH:
        recent_arith += 1
    if recent_arith >= 3:
        hints.append({
            "signal":           "repeated_core_arithmetic",
            "suggestion":       "core.add/sub/mul/div 를 3회 이상 연속 호출하고 있습니다. core.batch 로 묶으면 왕복 비용을 줄일 수 있습니다.",
            "recommended_tool": "core.batch",
        })

    # Rule 3: policy year stale
    if current_call.policy_year is not None and current_call.policy_year < _CURRENT_YEAR:
        hints.append({
            "signal":           "stale_policy_year",
            "suggestion":       f"정책 연도 {current_call.policy_year}가 현재 연도({_CURRENT_YEAR})보다 오래됐습니다. 최신 정책 연도를 확인하세요.",
            "recommended_tool": None,
        })

    # Rule 4: truncated trace
    if current_call.truncated:
        hints.append({
            "signal":           "trace_truncated",
            "suggestion":       "응답 페이로드가 SOOTOOL_MAX_PAYLOAD_KB 상한을 초과해 trace가 잘렸습니다. 환경변수를 상향하거나 trace_level=summary 를 사용하세요.",
            "recommended_tool": None,
        })

    # Rule 5: manual chain detection (heuristic: same session, >1 call, non-batch/pipeline)
    if _detect_manual_chain(history, current_call):
        hints.append({
            "signal":           "manual_chain_detected",
            "suggestion":       "이전 호출 결과를 수동으로 다음 입력에 전달하는 패턴이 감지됩니다. core.pipeline 으로 대체하면 결정론 체인을 보장할 수 있습니다.",
            "recommended_tool": "core.pipeline",
        })

    # Rule 6: 20+ single calls without batch
    total_single = _count_single_calls(history + [current_call])
    if total_single >= 20:
        hints.append({
            "signal":           "excessive_single_calls",
            "suggestion":       f"세션 내 단일 도구 호출이 {total_single}회 누적됐습니다. core.batch 없이 대량 단일 호출은 왕복 비효율을 유발합니다.",
            "recommended_tool": "core.batch",
        })

    return hints


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_trailing_arith(history: list[ToolCall]) -> int:
    """Count consecutive core arithmetic calls at the tail of history."""
    count = 0
    for call in reversed(history):
        if call.tool in _CORE_ARITH:
            count += 1
        else:
            break
    return count


def _detect_manual_chain(history: list[ToolCall], current: ToolCall) -> bool:
    """Heuristic: two or more non-batch/pipeline calls in the last 5, none of which is pipeline/batch."""
    if not history:
        return False
    _CHAIN_TOOLS = {"core.pipeline", "core.batch"}
    recent = list(history[-5:]) + [current]
    if any(c.tool in _CHAIN_TOOLS for c in recent):
        return False
    # If there are 3+ distinct non-batch/pipeline calls in recent window, flag it
    non_batch = [c for c in recent if c.tool not in _CHAIN_TOOLS]
    return len(non_batch) >= 3


def _count_single_calls(history: list[ToolCall]) -> int:
    """Count calls that are not core.batch or core.pipeline."""
    _BATCH_TOOLS = {"core.batch", "core.pipeline", "core.pipeline_resume"}
    return sum(1 for c in history if c.tool not in _BATCH_TOOLS)


def inject_meta(
    response: dict[str, Any],
    hints: list[dict[str, Any]],
    session_stats: dict[str, Any],
) -> dict[str, Any]:
    """Inject _meta.hints and _meta.session_stats into response.

    result and trace are never mutated (ADR-011 determinism guard).
    """
    result = dict(response)
    result["_meta"] = {
        "hints":         hints,
        "session_stats": session_stats,
    }
    return result
