"""Helper to enrich policy-aware tool responses with trace extension fields.

Adds policy_source, policy_audit_id, policy_sha256, policy_effective_date
to both the trace dict and the top-level response, and injects
override_policy_in_use hints when needed.

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

    # Top-level fields
    response["policy_source"]         = source
    response["policy_audit_id"]       = audit_id
    response["policy_sha256"]         = sha256
    response["policy_effective_date"] = eff_date

    # Enrich trace dict if present
    trace = response.get("trace")
    if isinstance(trace, dict):
        trace["policy_source"]         = source
        trace["policy_audit_id"]       = audit_id
        trace["policy_sha256"]         = sha256
        trace["policy_effective_date"] = eff_date

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
        meta = response.get("_meta")
        if meta is None:
            response["_meta"] = {"hints": [hint]}
        elif isinstance(meta, dict):
            hints = meta.get("hints")
            if hints is None:
                meta["hints"] = [hint]
            elif isinstance(hints, list):
                # Avoid duplicates
                signals = {h.get("signal") for h in hints}
                if "override_policy_in_use" not in signals:
                    hints.append(hint)

    return response


def _resolve_audit_id(source: str, policy_version: dict[str, Any]) -> str | None:
    """For override policies, look up the most recent activate audit entry."""
    if source != "override":
        return None
    # We don't cache the audit lookup — it's a one-time read per response
    return None  # Filled in by tools that have the draft_id available
