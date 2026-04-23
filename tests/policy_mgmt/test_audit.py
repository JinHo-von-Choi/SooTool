"""Tests for the JSONL audit log.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import stat

from sootool.policy_mgmt import audit


def test_append_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path))

    entry = audit.make_entry(
        action="activate",
        domain="tax",
        name="kr_income",
        year=2027,
        audit_id="aud-test-001",
    )
    audit.append_entry(entry)

    entries = audit.read_entries()
    assert len(entries) == 1
    assert entries[0]["audit_id"] == "aud-test-001"
    assert entries[0]["action"] == "activate"


def test_filter_by_domain_name(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path))

    audit.append_entry(audit.make_entry("activate", "tax", "kr_income", 2027, "aud-001"))
    audit.append_entry(audit.make_entry("rollback", "realestate", "kr_acquisition", 2026, "aud-002"))

    tax_entries = audit.read_entries(domain="tax")
    assert len(tax_entries) == 1
    assert tax_entries[0]["audit_id"] == "aud-001"

    re_entries = audit.read_entries(domain="realestate", name="kr_acquisition")
    assert len(re_entries) == 1


def test_append_only_permissions(tmp_path, monkeypatch):
    """Audit log file should have 0600 permissions."""
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path))

    audit.append_entry(audit.make_entry("import", "tax", "kr_income", 2027, "aud-perm-001"))

    from sootool.policy_mgmt.paths import get_audit_log_path
    log_path = get_audit_log_path()
    mode = stat.S_IMODE(log_path.stat().st_mode)
    assert mode == 0o600


def test_multiple_appends_order_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path))

    for i in range(5):
        audit.append_entry(audit.make_entry("activate", "tax", "kr_income", 2027, f"aud-{i:03d}"))

    entries = audit.read_entries()
    ids = [e["audit_id"] for e in entries]
    assert ids == [f"aud-{i:03d}" for i in range(5)]


def test_make_entry_structure() -> None:
    entry = audit.make_entry(
        action="propose",
        domain="tax",
        name="kr_income",
        year=2027,
        audit_id="aud-struct",
        draft_id="drf-abc",
        sha256_before="old",
        sha256_after="new",
        source_url="https://example.com",
        notice_no="고시 제1호",
    )
    assert "ts" in entry
    assert entry["action"] == "propose"
    assert entry["draft_id"] == "drf-abc"
    assert entry["sha256_before"] == "old"
    assert entry["sha256_after"] == "new"
