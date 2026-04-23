"""Draft lifecycle management — propose, update, gc, and promote policy drafts.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from sootool.policy_mgmt.paths import get_draft_dir

log = logging.getLogger("sootool.policy_mgmt.drafts")

_DRAFT_TTL_SECONDS = 24 * 3600  # 24 hours


def _new_draft_id() -> str:
    return f"drf-{uuid.uuid4().hex}"


def _ensure_draft_dir(draft_dir: Path) -> None:
    draft_dir.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to 0700
    try:
        os.chmod(draft_dir, 0o700)
    except OSError:
        log.warning("Could not set 0700 permissions on draft dir: %s", draft_dir)


def _draft_meta_path(draft_dir: Path, draft_id: str) -> Path:
    return draft_dir / f"{draft_id}.meta.json"


def _draft_yaml_path(draft_dir: Path, draft_id: str) -> Path:
    return draft_dir / f"{draft_id}.yaml"


def save_draft(
    domain:           str,
    name:             str,
    year:             int,
    yaml_content:     str,
    validation_report: dict[str, Any],
    source_url:       str = "",
    notice_no:        str = "",
    effective_date:   str = "",
    draft_id:         str | None = None,
) -> dict[str, Any]:
    """Save a policy draft, returning metadata with draft_id."""
    draft_dir = get_draft_dir()
    _ensure_draft_dir(draft_dir)

    did = draft_id if draft_id else _new_draft_id()
    now_ts = time.time()
    expires_at = now_ts + _DRAFT_TTL_SECONDS

    meta = {
        "draft_id":         did,
        "domain":           domain,
        "name":             name,
        "year":             year,
        "source_url":       source_url,
        "notice_no":        notice_no,
        "effective_date":   effective_date,
        "created_at":       now_ts,
        "expires_at":       expires_at,
        "validation":       validation_report,
    }

    meta_path = _draft_meta_path(draft_dir, did)
    yaml_path = _draft_yaml_path(draft_dir, did)

    # Atomic write: tmp -> fsync -> rename
    _atomic_write(meta_path, json.dumps(meta, ensure_ascii=False))
    _atomic_write(yaml_path, yaml_content)

    return meta


def _atomic_write(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.chmod(tmp_path, 0o600)
    try:
        with open(tmp_path, "r+b") as fh:
            os.fsync(fh.fileno())
    except OSError:
        pass
    os.replace(tmp_path, path)
    os.chmod(path, 0o600)


def load_draft(draft_id: str) -> dict[str, Any]:
    """Load a draft by ID, raising FileNotFoundError if missing or expired."""
    draft_dir = get_draft_dir()
    meta_path = _draft_meta_path(draft_dir, draft_id)
    yaml_path = _draft_yaml_path(draft_dir, draft_id)

    if not meta_path.exists() or not yaml_path.exists():
        raise FileNotFoundError(f"Draft not found: {draft_id}")

    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    if time.time() > meta.get("expires_at", 0):
        _delete_draft_files(draft_dir, draft_id)
        raise FileNotFoundError(f"Draft expired and removed: {draft_id}")

    meta["yaml_content"] = yaml_path.read_text(encoding="utf-8")
    return meta


def delete_draft(draft_id: str) -> None:
    """Delete a draft by ID."""
    draft_dir = get_draft_dir()
    _delete_draft_files(draft_dir, draft_id)


def _delete_draft_files(draft_dir: Path, draft_id: str) -> None:
    for path in (
        _draft_meta_path(draft_dir, draft_id),
        _draft_yaml_path(draft_dir, draft_id),
    ):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            log.warning("Could not remove draft file: %s", path)


def gc_expired_drafts() -> int:
    """Remove expired draft files. Returns count of removed drafts."""
    draft_dir = get_draft_dir()
    if not draft_dir.exists():
        return 0

    removed = 0
    now = time.time()
    for meta_path in draft_dir.glob("*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if now > meta.get("expires_at", 0):
                draft_id = meta.get("draft_id", meta_path.stem.replace(".meta", ""))
                _delete_draft_files(draft_dir, draft_id)
                removed += 1
        except Exception:
            log.warning("Error during draft GC for: %s", meta_path, exc_info=True)

    if removed:
        log.info("GC removed %d expired draft(s)", removed)
    return removed
