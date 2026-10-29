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


# 정책 파일을 실제로 유효하게 만든 감사 동작. activate 는 새로 활성화하고, rollback 은
# 이전 버전으로 되돌리고, import 는 외부 정책 묶음을 설치한다. 셋 다 결과적으로 어떤
# 정책 파일이 현재 유효한 버전이 되는 원인이므로 감사 id 전파 대상이다.
_AUDIT_ACTIVATING_ACTIONS = frozenset({"activate", "rollback", "import"})


def _resolve_audit_id(source: str, policy_version: dict[str, Any]) -> str | None:
    """덮어쓰기 정책의 출처 감사 id를 찾는다.

    ADR-016: "audit_id 는 계산 도구 trace 에 ``policy_audit_id`` 로 전파된다."
    정책 파일의 sha256 로 감사 로그를 역순 탐색해, 그 해시를 유효하게 만든 가장 최근
    항목을 찾는다. sha256 이 다르면 같은 파일명이 다른 내용이거나 다른 연도 버전이므로
    구분할 수 없다.

    정책이 패키지 기본값이면 전파할 감사 id 가 없다(사용자가 바꾼 적이 없다).
    """
    if source != "override":
        return None

    sha = policy_version.get("sha256")
    if not sha:
        return None

    try:
        from sootool.policy_mgmt.audit import read_entries
        entries = read_entries()
    except OSError:
        return None

    # 감사 로그는 append-only 이므로 뒤에서부터 찾으면 가장 최근 항목이 먼저 나온다.
    for entry in reversed(entries):
        if entry.get("action") not in _AUDIT_ACTIVATING_ACTIONS:
            continue
        if entry.get("sha256_after") != sha:
            continue
        audit_id = entry.get("audit_id")
        if audit_id:
            return str(audit_id)
    return None
