"""Append-only JSONL audit log for policy management operations.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import json
import logging
import os
import stat
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sootool.policy_mgmt.paths import get_audit_log_path

log = logging.getLogger("sootool.policy_mgmt.audit")

_WRITE_LOCK = threading.Lock()


def _ensure_audit_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600)
    else:
        # Enforce 0600 permissions
        current = stat.S_IMODE(path.stat().st_mode)
        if current != 0o600:
            try:
                os.chmod(path, 0o600)
            except OSError:
                log.warning("Could not set 0600 permissions on audit log: %s", path)


def append_entry(entry: dict[str, Any]) -> None:
    """Append a single JSON entry to the audit log (thread-safe, append-only)."""
    path = get_audit_log_path()
    with _WRITE_LOCK:
        _ensure_audit_file(path)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def read_entries(
    domain: str | None = None,
    name:   str | None = None,
) -> list[dict[str, Any]]:
    """Read audit log entries, optionally filtered by domain/name."""
    path = get_audit_log_path()
    if not path.exists():
        return []

    results: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if domain and entry.get("domain") != domain:
                continue
            if name and entry.get("name") != name:
                continue
            results.append(entry)

    return results


def make_entry(
    action:       str,
    domain:       str,
    name:         str,
    year:         int,
    audit_id:     str,
    draft_id:     str | None = None,
    sha256_before: str | None = None,
    sha256_after:  str | None = None,
    source_url:   str | None = None,
    notice_no:    str | None = None,
    validation:   dict[str, Any] | None = None,
    actor:        str = "user:cli",
) -> dict[str, Any]:
    """Build a complete audit log entry."""
    return {
        "ts":           datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_id":     audit_id,
        "actor":        actor,
        "action":       action,
        "domain":       domain,
        "name":         name,
        "year":         year,
        "draft_id":     draft_id,
        "sha256_before": sha256_before,
        "sha256_after":  sha256_after,
        "source_url":   source_url,
        "notice_no":    notice_no,
        "validation":   validation or {"status": "ok", "findings": []},
    }
