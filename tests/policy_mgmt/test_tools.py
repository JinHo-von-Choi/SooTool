"""Tests for all 10 policy_mgmt MCP tools.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import re
import textwrap

import pytest


def _make_income_yaml(year: int = 2027) -> str:
    body = textwrap.dedent(f"""\
        sha256: "PLACEHOLDER"
        effective_date: "{year}-01-01"
        notice_no: "고시-test-{year}"
        source_url: "https://example.com"
        data:
          brackets:
            - upper: 14000000
              rate: 0.06
            - upper: null
              rate: 0.15
    """)
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    return body.replace("PLACEHOLDER", real_hash)


# ---------------------------------------------------------------------------
# policy_list
# ---------------------------------------------------------------------------

def test_policy_list_returns_policies():
    from sootool.policy_mgmt.tools import policy_list
    result = policy_list()
    assert "policies" in result
    assert result["count"] > 0


# ---------------------------------------------------------------------------
# policy_get
# ---------------------------------------------------------------------------

def test_policy_get_package():
    from sootool.policy_mgmt import loader
    from sootool.policy_mgmt.tools import policy_get
    loader.invalidate_cache()
    result = policy_get("tax", "kr_income", 2026)
    assert result["source"] == "package"
    assert "data" in result


def test_policy_get_unknown_year():
    from sootool.policies import UnsupportedPolicyError
    from sootool.policy_mgmt.tools import policy_get
    with pytest.raises(UnsupportedPolicyError):
        policy_get("tax", "kr_income", 1900)


# ---------------------------------------------------------------------------
# policy_history
# ---------------------------------------------------------------------------

def test_policy_history_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path))
    from sootool.policy_mgmt.tools import policy_history
    result = policy_history("tax", "kr_income")
    assert "entries" in result
    assert isinstance(result["entries"], list)


# ---------------------------------------------------------------------------
# policy_diff
# ---------------------------------------------------------------------------

def test_policy_diff_year_from_to():
    from sootool.policy_mgmt import loader
    from sootool.policy_mgmt.tools import policy_diff
    loader.invalidate_cache()
    result = policy_diff("tax", "kr_income", year_from=2026, year_to=2026)
    assert "changes" in result
    assert result["changes"] == []


def test_policy_diff_missing_args():
    from sootool.policy_mgmt.tools import policy_diff
    result = policy_diff("tax", "kr_income")
    assert "error" in result


# ---------------------------------------------------------------------------
# policy_validate
# ---------------------------------------------------------------------------

def test_policy_validate_valid():
    from sootool.policy_mgmt.tools import policy_validate
    yaml_content = _make_income_yaml()
    result = policy_validate(yaml_content, domain="tax", name="kr_income")
    assert result["status"] == "ok"


def test_policy_validate_bad_yaml():
    from sootool.policy_mgmt.tools import policy_validate
    result = policy_validate("{ invalid: yaml:: :", domain="tax")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Admin gate — all write tools must return admin_required when not in admin mode
# ---------------------------------------------------------------------------

def test_policy_propose_requires_admin(monkeypatch):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    from sootool.policy_mgmt.tools import policy_propose
    result = policy_propose("tax", "kr_income", 2027, _make_income_yaml())
    assert result.get("error") == "admin_required"


def test_policy_activate_requires_admin(monkeypatch):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    from sootool.policy_mgmt.tools import policy_activate
    result = policy_activate("drf-fakeid")
    assert result.get("error") == "admin_required"


def test_policy_rollback_requires_admin(monkeypatch):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    from sootool.policy_mgmt.tools import policy_rollback
    result = policy_rollback("tax", "kr_income", 2027)
    assert result.get("error") == "admin_required"


def test_policy_import_requires_admin(monkeypatch):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    from sootool.policy_mgmt.tools import policy_import
    result = policy_import({"yaml_content": "", "metadata": {}})
    assert result.get("error") == "admin_required"


# ---------------------------------------------------------------------------
# policy_propose + policy_activate full flow
# ---------------------------------------------------------------------------

def test_propose_and_activate_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))

    from sootool.policy_mgmt import loader
    loader.invalidate_cache()

    from sootool.policy_mgmt.tools import policy_activate, policy_propose

    yaml_content = _make_income_yaml(2027)
    propose_result = policy_propose(
        domain="tax",
        name="kr_income",
        year=2027,
        yaml_content=yaml_content,
        source_url="https://example.com",
        notice_no="고시 제1호",
    )
    assert "draft_id" in propose_result
    assert propose_result.get("validation", {}).get("status") in ("ok", "warning")

    draft_id = propose_result["draft_id"]
    activate_result = policy_activate(draft_id)
    assert activate_result["activated"] is True
    assert activate_result["source"] == "override"
    assert "audit_id" in activate_result

    # Verify it is now loaded as override
    loader.invalidate_cache()
    doc = loader.load("tax", "kr_income", 2027)
    assert doc["source"] == "override"

    # Cleanup
    loader.invalidate_cache()


# ---------------------------------------------------------------------------
# policy_rollback
# ---------------------------------------------------------------------------

def test_rollback_removes_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))

    from sootool.policy_mgmt import loader
    loader.invalidate_cache()

    from sootool.policy_mgmt.tools import policy_activate, policy_propose, policy_rollback

    yaml_content = _make_income_yaml(2027)
    propose_result = policy_propose("tax", "kr_income", 2027, yaml_content)
    activate_result = policy_activate(propose_result["draft_id"])
    assert activate_result["activated"] is True

    rollback_result = policy_rollback("tax", "kr_income", 2027)
    assert rollback_result["rolled_back"] is True
    assert "audit_id" in rollback_result

    loader.invalidate_cache()


def test_rollback_nonexistent_is_graceful(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    from sootool.policy_mgmt.tools import policy_rollback
    result = policy_rollback("tax", "kr_income", 1900)
    assert result["rolled_back"] is False


# ---------------------------------------------------------------------------
# policy_export + policy_import
# ---------------------------------------------------------------------------

def test_export_import_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))

    from sootool.policy_mgmt import loader
    loader.invalidate_cache()

    from sootool.policy_mgmt.tools import policy_export, policy_import

    export_result = policy_export("tax", "kr_income", 2026)
    assert "bundle" in export_result

    bundle = export_result["bundle"]
    import_result = policy_import(bundle)
    assert import_result["imported"] is True

    loader.invalidate_cache()


def test_import_invalid_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    from sootool.policy_mgmt.tools import policy_import
    result = policy_import({"yaml_content": "invalid", "metadata": {"domain": "tax", "name": "kr_income", "year": 2027}})
    assert result.get("error") in ("validation_failed", "invalid_bundle") or "error" in result
