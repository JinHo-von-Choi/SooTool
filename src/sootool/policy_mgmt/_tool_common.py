"""정책 관리 도구의 공용 보조: 관리자 게이트, 감사 id, 원자적 쓰기, 저장 경로 결정.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

import yaml

from sootool.core.request_context import SCOPE_POLICY_WRITE, has_scope
from sootool.policy_mgmt import loader
from sootool.policy_mgmt.paths import (
    contained_path,
    ensure_private_dir,
    get_override_policy_dir,
    get_package_policy_dir,
    safe_component,
    safe_iso_date,
)

log = logging.getLogger("sootool.policy_mgmt.tools")


_ADMIN_REQUIRED_ERROR = {
    "error":   "admin_required",
    "message": (
        "This tool requires admin mode. Set SOOTOOL_ADMIN_MODE=1 "
        "or start the server with --admin."
    ),
}


def _is_admin() -> bool:
    """관리자 모드가 켜져 있고 현재 요청이 policy-write 범위를 가졌는지 반환한다.

    로컬 전송(stdio, unix)과 프로세스 내 호출은 범위 검사를 하지 않는다. 네트워크 전송은
    관리자 토큰으로 인증한 요청만 policy-write 범위를 갖는다.
    """
    mode_on = os.environ.get("SOOTOOL_ADMIN_MODE", "").strip() in ("1", "true", "yes")
    return mode_on and has_scope(SCOPE_POLICY_WRITE)


def _require_admin() -> dict[str, Any] | None:
    if not _is_admin():
        return _ADMIN_REQUIRED_ERROR
    return None


def _new_audit_id() -> str:
    return f"aud-{uuid.uuid4().hex}"


def _atomic_write_yaml(yaml_path: Path, content: str) -> None:
    """Write content to yaml_path atomically via tmp -> fsync -> rename."""
    ensure_private_dir(yaml_path.parent)
    tmp = yaml_path.with_suffix(".yaml.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.chmod(tmp, 0o600)
    try:
        with open(tmp, "r+b") as fh:
            os.fsync(fh.fileno())
    except OSError:
        pass
    os.replace(tmp, yaml_path)
    os.chmod(yaml_path, 0o600)


def _target_path(domain: str, name: str, year: int, yaml_content: str) -> Path:
    """새 정책 문서를 저장할 덮어쓰기 경로. 시행일이 다른 새 버전이면 ``@<시행일>`` 이 붙는다."""
    safe_component(domain, "domain")
    safe_component(name, "name")
    doc       = yaml.safe_load(yaml_content)
    raw       = doc.get("effective_date", "") if isinstance(doc, dict) else ""
    effective = safe_iso_date(raw, "effective_date") if raw not in ("", None) else ""
    filename  = loader.version_filename(domain, name, int(year), effective) if effective else f"{name}_{int(year)}.yaml"
    return contained_path(get_override_policy_dir(), get_override_policy_dir() / domain / filename)


def _existing_sha256(domain: str, filename: str) -> str | None:
    """같은 파일 이름의 기존 문서(덮어쓰기 우선)의 sha256. 없으면 None."""
    for base in (get_override_policy_dir(), get_package_policy_dir()):
        path = base / domain / filename
        if path.exists():
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
                return str(doc.get("sha256", "")) if isinstance(doc, dict) else None
            except Exception:
                log.debug("Could not read sha256 from %s", path, exc_info=True)
    return None
