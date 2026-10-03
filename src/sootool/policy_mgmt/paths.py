"""XDG-aware path resolution for policy override and draft directories.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

from sootool.core.errors import UnsafeDirectoryError

log = logging.getLogger("sootool.policy_mgmt.paths")


def _xdg_data_home() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


def _xdg_state_home() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME", "")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "state"


def _xdg_runtime_dir() -> Path:
    xdg = os.environ.get("XDG_RUNTIME_DIR", "")
    if xdg:
        return Path(xdg)
    return _xdg_state_home()


def ensure_private_dir(path: Path) -> None:
    """디렉터리를 소유자 전용(0700)으로 준비한다.

    없으면 만들고, 심볼릭 링크이거나 디렉터리가 아니거나 다른 사용자 소유이면
    UnsafeDirectoryError 를 낸다. 소유자는 맞지만 그룹·기타 권한이 열려 있으면 0700 으로 좁힌다.
    """
    path.mkdir(parents=True, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise UnsafeDirectoryError(f"심볼릭 링크는 저장 디렉터리로 쓸 수 없습니다: {path}")
    if not stat.S_ISDIR(info.st_mode):
        raise UnsafeDirectoryError(f"디렉터리가 아닙니다: {path}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise UnsafeDirectoryError(f"다른 사용자 소유 디렉터리는 쓸 수 없습니다: {path}")
    if stat.S_IMODE(info.st_mode) & 0o077:
        try:
            os.chmod(path, 0o700)
        except OSError as exc:
            raise UnsafeDirectoryError(f"디렉터리 권한을 0700 으로 좁히지 못했습니다: {path}") from exc


def get_override_policy_dir() -> Path:
    """Return the user override policy directory.

    Priority: SOOTOOL_POLICY_DIR > $XDG_DATA_HOME/sootool/policies/ > ~/.local/share/...
    """
    env = os.environ.get("SOOTOOL_POLICY_DIR", "")
    if env:
        return Path(env)
    return _xdg_data_home() / "sootool" / "policies"


def get_draft_dir() -> Path:
    """Return the draft storage directory.

    Priority: SOOTOOL_DRAFT_DIR > $XDG_RUNTIME_DIR/sootool/drafts/ > $XDG_STATE_HOME/sootool/drafts/ > ~/.local/state/...
    """
    env = os.environ.get("SOOTOOL_DRAFT_DIR", "")
    if env:
        return Path(env)
    return _xdg_runtime_dir() / "sootool" / "drafts"


def get_audit_log_path() -> Path:
    """Return path to the JSONL audit log file.

    Priority: SOOTOOL_STATE_DIR > $XDG_STATE_HOME/sootool/policy_audit.jsonl > ~/.local/state/...
    """
    env = os.environ.get("SOOTOOL_STATE_DIR", "")
    if env:
        return Path(env) / "policy_audit.jsonl"
    return _xdg_state_home() / "sootool" / "policy_audit.jsonl"


def get_package_policy_dir() -> Path:
    """Return the package-bundled (read-only) policy base directory."""
    from sootool.policies import _POLICIES_DIR
    return Path(_POLICIES_DIR)


def log_override_dir_info() -> None:
    """Log the effective override policy directory at INFO level on startup."""
    override_dir = get_override_policy_dir()
    log.info("Policy override directory: %s", override_dir)
