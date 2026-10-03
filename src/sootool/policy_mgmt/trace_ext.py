"""Helper to enrich policy-aware tool responses with trace extension fields.

Adds policy_source, policy_audit_id, policy_sha256, policy_effective_date,
policy_status (enacted | proposed | superseded), policy_effective_to and
policy_citations to both the trace dict and the top-level response, and injects
override_policy_in_use and proposed_policy_in_use hints when needed.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from typing import Any


def enrich_response(
    response: dict[str, Any],
    policy_doc: dict[str, Any],
) -> dict[str, Any]:
    """Add policy_source/audit_id/sha256/effective_date to response and trace.

    Mutates and returns the response dict.
    """
    source    = policy_doc.get("source", "package")
    pv        = policy_doc.get("policy_version", {})
    sha256    = pv.get("sha256", "")
    eff_date  = pv.get("effective_date", "")
    audit_id  = _resolve_audit_id(source, pv)
    status    = pv.get("status", "enacted")
    fields    = {
        "policy_source":         source,
        "policy_audit_id":       audit_id,
        "policy_sha256":         sha256,
        "policy_effective_date": eff_date,
        "policy_effective_to":   pv.get("effective_to"),
        "policy_status":         status,
        "policy_citations":      pv.get("citations", []),
    }

    # Top-level fields and the trace dict
    response.update(fields)
    trace = response.get("trace")
    if isinstance(trace, dict):
        trace.update(fields)

    if status == "proposed":
        _add_hint(response, {
            "signal":           "proposed_policy_in_use",
            "suggestion":       (
                "이 결과는 국회 확정 전 개정안(proposed) 정책을 사용합니다. 확정 전에는 법적 효력이 "
                "없으며 개정안이 바뀔 수 있습니다. policy_status 와 policy_effective_date 를 확인하세요."
            ),
            "recommended_tool": None,
        })

    # Inject _meta.hints when override is in use
    if source == "override":
        hint = {
            "signal":          "override_policy_in_use",
            "suggestion":      (
                "이 결과는 사용자 덮어쓰기 정책을 사용합니다. "
                "policy_history로 변경 이력을 확인하세요."
            ),
            "recommended_tool": "sootool.policy_history",
        }
        _add_hint(response, hint)

    return response


def _add_hint(response: dict[str, Any], hint: dict[str, Any]) -> None:
    """응답의 _meta.hints 에 힌트를 중복 없이 추가한다."""
    meta = response.get("_meta")
    if meta is None:
        response["_meta"] = {"hints": [hint]}
    elif isinstance(meta, dict):
        hints = meta.get("hints")
        if hints is None:
            meta["hints"] = [hint]
        elif isinstance(hints, list):
            signals = {h.get("signal") for h in hints}
            if hint["signal"] not in signals:
                hints.append(hint)


def _resolve_audit_id(source: str, policy_version: dict[str, Any]) -> str | None:
    """For override policies, look up the most recent activate audit entry."""
    if source != "override":
        return None
    # We don't cache the audit lookup, it's a one-time read per response
    return None  # Filled in by tools that have the draft_id available
