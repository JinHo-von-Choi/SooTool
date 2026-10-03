"""XDG-aware path resolution for policy override and draft directories.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import logging
import os
import re
import stat
from datetime import date
from pathlib import Path

from sootool.core.errors import InvalidInputError, UnsafeDirectoryError

log = logging.getLogger("sootool.policy_mgmt.paths")


_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9_]{1,64}")
_SAFE_ID        = re.compile(r"[A-Za-z0-9_-]{1,80}")


def safe_component(value: object, label: str) -> str:
    """파일 이름의 일부가 되는 값(영역, 정책 이름)이 영문, 숫자, 밑줄만 쓰는지 확인한다."""
    if not isinstance(value, str) or _SAFE_COMPONENT.fullmatch(value) is None:
        raise InvalidInputError(f"{label} 는 영문, 숫자, 밑줄 1~64자여야 합니다.")
    return value


def safe_id(value: object, label: str) -> str:
    """초안 식별자가 영문, 숫자, 밑줄, 하이픈만 쓰는지 확인한다."""
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise InvalidInputError(f"{label} 는 영문, 숫자, 밑줄, 하이픈 1~80자여야 합니다.")
    return value


def safe_iso_date(value: object, label: str) -> str:
    """ISO 날짜(YYYY-MM-DD) 문자열로 정규화한다. 날짜 형식이 아니면 거부한다."""
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise InvalidInputError(f"{label} 는 YYYY-MM-DD 형식이어야 합니다.") from exc


def contained_path(base: Path, candidate: Path) -> Path:
    """candidate 가 base 아래에 있는지 확인하고 반환한다."""
    if not candidate.resolve().is_relative_to(base.resolve()):
        raise InvalidInputError("정책 저장 경로가 허용된 디렉터리를 벗어납니다.")
    return candidate


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


def get_runtime_dir() -> Path:
    """런타임 파일(초안, 소켓)의 기본 위치. $XDG_RUNTIME_DIR, 없으면 상태 디렉터리."""
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
    return get_runtime_dir() / "sootool" / "drafts"


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
