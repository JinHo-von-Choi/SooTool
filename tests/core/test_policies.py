"""
Tests for policies/__init__.py — YAML policy loader with SHA256 integrity check.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from sootool.policies import PolicyIntegrityError, UnsupportedPolicyError, load


class TestPoliciesLoad:
    def test_load_returns_dict(self):
        result = load("tax", "kr_income", 2026)
        assert isinstance(result, dict)

    def test_load_has_data_key(self):
        result = load("tax", "kr_income", 2026)
        assert "data" in result

    def test_load_data_has_brackets(self):
        result = load("tax", "kr_income", 2026)
        assert "brackets" in result["data"]
        assert len(result["data"]["brackets"]) > 0

    def test_load_has_policy_version(self):
        result = load("tax", "kr_income", 2026)
        assert "policy_version" in result

    def test_policy_version_has_required_fields(self):
        pv = load("tax", "kr_income", 2026)["policy_version"]
        assert "year"           in pv
        assert "sha256"         in pv
        assert "effective_date" in pv
        assert "notice_no"      in pv

    def test_policy_version_year(self):
        pv = load("tax", "kr_income", 2026)["policy_version"]
        assert pv["year"] == 2026

    def test_brackets_have_required_fields(self):
        brackets = load("tax", "kr_income", 2026)["data"]["brackets"]
        for bracket in brackets:
            assert "rate" in bracket
            assert "upper" in bracket

    def test_cache_returns_same_dict(self):
        """Acceptance test: calling load twice returns the identical dict (same id)."""
        r1 = load("tax", "kr_income", 2026)
        r2 = load("tax", "kr_income", 2026)
        assert r1 is r2


class TestIntegrityCheck:
    def test_corrupted_file_raises_integrity_error(self, tmp_path, monkeypatch):
        """
        Acceptance test: load, then manually corrupt the YAML -> PolicyIntegrityError.
        We monkeypatch the policies directory to a temp location.
        """
        import sootool.policies as policies_module

        # Copy the real policy file into tmp_path
        src_dir = Path(policies_module.__file__).parent / "tax"
        dst_dir = tmp_path / "tax"
        shutil.copytree(src_dir, dst_dir)

        # Monkeypatch _POLICIES_DIR to point to tmp_path
        monkeypatch.setattr(policies_module, "_POLICIES_DIR", tmp_path)

        # Clear the lru_cache before the test
        policies_module.load.cache_clear()

        # First load should succeed
        result = policies_module.load("tax", "kr_income", 2026)
        assert "data" in result

        # Corrupt: change a rate value in the file
        yaml_file = dst_dir / "kr_income_2026.yaml"
        content   = yaml_file.read_text(encoding="utf-8")
        corrupted = content.replace("0.06", "0.99")
        yaml_file.write_text(corrupted, encoding="utf-8")

        # Clear cache so the file is re-read
        policies_module.load.cache_clear()

        with pytest.raises(PolicyIntegrityError):
            policies_module.load("tax", "kr_income", 2026)

        # Restore cache clear so other tests are not affected
        policies_module.load.cache_clear()

    def test_pristine_file_passes_integrity(self):
        """The unmodified kr_income_2026.yaml must pass integrity check on load."""
        result = load("tax", "kr_income", 2026)
        assert result is not None


class TestUnsupportedPolicyError:
    def test_missing_year_raises_unsupported(self):
        """Acceptance test: load("tax", "kr_income", 2099) -> UnsupportedPolicyError."""
        with pytest.raises(UnsupportedPolicyError) as exc_info:
            load("tax", "kr_income", 2099)
        err = exc_info.value
        assert err.domain == "tax"
        assert err.key    == "kr_income"
        assert err.year   == 2099

    def test_unsupported_error_has_supported_years(self):
        """supported_years must contain 2026."""
        with pytest.raises(UnsupportedPolicyError) as exc_info:
            load("tax", "kr_income", 2099)
        assert 2026 in exc_info.value.supported_years

    def test_missing_domain_raises_unsupported(self):
        with pytest.raises(UnsupportedPolicyError):
            load("nonexistent_domain", "some_key", 2026)
