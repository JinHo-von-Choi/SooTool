from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from sootool.core.errors import SooToolError, UnsafeDirectoryError
from sootool.policy_mgmt import paths
from sootool.policy_mgmt.paths import ensure_private_dir, get_draft_dir


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


# --- 기본 경로 ---

def test_draft_dir_prefers_explicit_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "custom"))
    assert get_draft_dir() == tmp_path / "custom"


def test_draft_dir_uses_runtime_dir_when_available(monkeypatch, tmp_path):
    monkeypatch.delenv("SOOTOOL_DRAFT_DIR", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    assert get_draft_dir() == tmp_path / "run" / "sootool" / "drafts"


def test_draft_dir_falls_back_to_state_dir_never_tmp(monkeypatch, tmp_path):
    monkeypatch.delenv("SOOTOOL_DRAFT_DIR", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert get_draft_dir() == tmp_path / "state" / "sootool" / "drafts"


def test_draft_dir_default_is_under_home_state_without_any_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("SOOTOOL_DRAFT_DIR", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert get_draft_dir() == tmp_path / ".local" / "state" / "sootool" / "drafts"


# --- ensure_private_dir ---

def test_creates_missing_directory_with_owner_only_mode(tmp_path):
    target = tmp_path / "a" / "b"
    ensure_private_dir(target)
    assert target.is_dir()
    assert _mode(target) == 0o700


def test_narrows_open_permissions_on_existing_directory(tmp_path):
    target = tmp_path / "open"
    target.mkdir()
    os.chmod(target, 0o755)  # noqa: S103
    ensure_private_dir(target)
    assert _mode(target) == 0o700


def test_existing_private_directory_is_left_alone(tmp_path):
    target = tmp_path / "ok"
    target.mkdir(mode=0o700)
    os.chmod(target, 0o700)
    ensure_private_dir(target)
    assert _mode(target) == 0o700


def test_symbolic_link_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(UnsafeDirectoryError):
        ensure_private_dir(link)


def test_regular_file_is_refused(tmp_path):
    target = tmp_path / "file"
    target.write_text("x", encoding="utf-8")
    with pytest.raises((UnsafeDirectoryError, FileExistsError)):
        ensure_private_dir(target)


def test_directory_owned_by_another_user_is_refused(tmp_path, monkeypatch):
    target = tmp_path / "foreign"
    target.mkdir()
    other_uid = os.getuid() + 1
    monkeypatch.setattr(paths.os, "getuid", lambda: other_uid)
    with pytest.raises(UnsafeDirectoryError):
        ensure_private_dir(target)


def test_unsafe_directory_error_is_a_typed_tool_error():
    assert issubclass(UnsafeDirectoryError, SooToolError)


# --- 저장소 연동 ---

def test_draft_save_creates_private_directory_and_files(monkeypatch, tmp_path):
    from sootool.policy_mgmt.drafts import save_draft

    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    meta = save_draft("tax", "kr_income", 2026, "a: 1\n", {"status": "ok"})
    draft_dir = tmp_path / "drafts"
    assert _mode(draft_dir) == 0o700
    assert (draft_dir / f"{meta['draft_id']}.yaml").exists()


def test_draft_save_refuses_symlinked_draft_directory(monkeypatch, tmp_path):
    from sootool.policy_mgmt.drafts import save_draft

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "drafts"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(link))
    with pytest.raises(UnsafeDirectoryError):
        save_draft("tax", "kr_income", 2026, "a: 1\n", {"status": "ok"})
    assert list(real.iterdir()) == []


def test_audit_log_directory_is_private(monkeypatch, tmp_path):
    from sootool.policy_mgmt import audit

    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    audit.append_entry({"event": "x"})
    assert _mode(tmp_path / "state") == 0o700
    assert _mode(tmp_path / "state" / "policy_audit.jsonl") == 0o600
