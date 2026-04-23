"""Tests for draft lifecycle management.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import pytest

from sootool.policy_mgmt import drafts


def _sample_yaml() -> str:
    return (
        'sha256: "abc"\n'
        'effective_date: "2027-01-01"\n'
        'notice_no: "test"\n'
        'source_url: "https://example.com"\n'
        'data:\n'
        '  brackets:\n'
        '    - upper: null\n'
        '      rate: 0.10\n'
    )


def test_save_and_load_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))

    meta = drafts.save_draft(
        domain="tax",
        name="kr_income",
        year=2027,
        yaml_content=_sample_yaml(),
        validation_report={"status": "ok", "findings": []},
    )
    did = meta["draft_id"]
    assert did.startswith("drf-")

    loaded = drafts.load_draft(did)
    assert loaded["domain"] == "tax"
    assert loaded["name"] == "kr_income"
    assert loaded["year"] == 2027
    assert loaded["yaml_content"] == _sample_yaml()

    drafts.delete_draft(did)
    with pytest.raises(FileNotFoundError):
        drafts.load_draft(did)


def test_draft_expiry(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setattr(drafts, "_DRAFT_TTL_SECONDS", -1)  # immediate expiry

    meta = drafts.save_draft(
        domain="tax",
        name="kr_income",
        year=2027,
        yaml_content=_sample_yaml(),
        validation_report={"status": "ok", "findings": []},
    )
    did = meta["draft_id"]

    with pytest.raises(FileNotFoundError):
        drafts.load_draft(did)


def test_gc_removes_expired(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setattr(drafts, "_DRAFT_TTL_SECONDS", -1)

    drafts.save_draft(
        domain="tax",
        name="kr_income",
        year=2027,
        yaml_content=_sample_yaml(),
        validation_report={"status": "ok", "findings": []},
    )
    removed = drafts.gc_expired_drafts()
    assert removed == 1

    # File should be gone
    draft_dir = tmp_path / "drafts"
    remaining = list(draft_dir.glob("*.yaml"))
    assert len(remaining) == 0


def test_gc_keeps_valid_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))

    meta = drafts.save_draft(
        domain="tax",
        name="kr_income",
        year=2027,
        yaml_content=_sample_yaml(),
        validation_report={"status": "ok", "findings": []},
    )
    removed = drafts.gc_expired_drafts()
    assert removed == 0

    drafts.delete_draft(meta["draft_id"])


def test_atomic_write_permissions(tmp_path, monkeypatch):
    """Draft files should have 0600 permissions."""
    import stat as stat_mod
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))

    meta = drafts.save_draft(
        domain="tax",
        name="kr_income",
        year=2027,
        yaml_content=_sample_yaml(),
        validation_report={"status": "ok", "findings": []},
    )
    did = meta["draft_id"]
    draft_dir = tmp_path / "drafts"
    yaml_path = draft_dir / f"{did}.yaml"
    mode = stat_mod.S_IMODE(yaml_path.stat().st_mode)
    assert mode == 0o600

    drafts.delete_draft(did)
