"""Tests for dual-store policy loader priority logic.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from sootool.policies import UnsupportedPolicyError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_income_yaml(year: int, sha256_placeholder: str = "PLACEHOLDER") -> str:
    """Build a minimal kr_income YAML for testing."""
    import hashlib
    import re

    body = textwrap.dedent(f"""\
        sha256: "{sha256_placeholder}"
        effective_date: "{year}-01-01"
        notice_no: "test-notice-{year}"
        source_url: "https://example.com"
        data:
          brackets:
            - upper: 14000000
              rate: 0.06
            - upper: null
              rate: 0.15
    """)
    # Compute real sha256 over content with sha256 line stripped
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    return body.replace(sha256_placeholder, real_hash)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_package_load(tmp_path: Path) -> None:
    """Loader falls back to package store when no override exists."""
    from sootool.policy_mgmt import loader
    loader.invalidate_cache()

    doc = loader.load("tax", "kr_income", 2026)
    assert doc["source"] == "package"
    assert "brackets" in doc["data"]


def test_override_takes_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Override directory file takes priority over package."""
    from sootool.policy_mgmt import loader

    override_dir = tmp_path / "policies" / "tax"
    override_dir.mkdir(parents=True)
    yaml_content = _make_income_yaml(2026)
    (override_dir / "kr_income_2026.yaml").write_text(yaml_content, encoding="utf-8")

    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    loader.invalidate_cache()

    doc = loader.load("tax", "kr_income", 2026)
    assert doc["source"] == "override"

    loader.invalidate_cache()


def test_unsupported_year_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UnsupportedPolicyError raised when year has no file in either store."""
    from sootool.policy_mgmt import loader

    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    loader.invalidate_cache()

    with pytest.raises(UnsupportedPolicyError):
        loader.load("tax", "kr_income", 1900)

    loader.invalidate_cache()


def test_cache_invalidation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """invalidate_cache removes cached entries."""
    from sootool.policy_mgmt import loader

    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    loader.invalidate_cache()

    doc1 = loader.load("tax", "kr_income", 2026)
    loader.invalidate_cache(domain="tax", key="kr_income", year=2026)
    doc2 = loader.load("tax", "kr_income", 2026)
    assert doc1["source"] == doc2["source"]

    loader.invalidate_cache()


def test_list_available_policies() -> None:
    """list_available_policies returns at least the package bundled policies."""
    from sootool.policy_mgmt import loader

    policies = loader.list_available_policies()
    assert len(policies) > 0
    names = {(p["domain"], p["name"]) for p in policies}
    assert ("tax", "kr_income") in names


def test_override_env_variable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SOOTOOL_POLICY_DIR env variable sets the override directory."""
    from sootool.policy_mgmt.paths import get_override_policy_dir

    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "mypolicies"))
    expected = tmp_path / "mypolicies"
    assert get_override_policy_dir() == expected
