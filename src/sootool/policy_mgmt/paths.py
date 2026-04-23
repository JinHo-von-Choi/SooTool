"""XDG-aware path resolution for policy override and draft directories.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

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
    uid = os.getuid()
    return Path(f"/tmp/sootool-drafts-{uid}")  # noqa: S108


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

    Priority: SOOTOOL_DRAFT_DIR > $XDG_RUNTIME_DIR/sootool/drafts/ > /tmp/sootool-drafts-<uid>/
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
