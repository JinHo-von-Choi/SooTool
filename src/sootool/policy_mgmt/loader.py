"""Dual-store policy loader with versioned, time-aware resolution.

정책은 ``<key>_<year>.yaml`` 이며, 같은 연도 안에서 시행일이 다른 버전은
``<key>_<year>@<시행일>.yaml`` 로 둔다. 호출은 해석 컨텍스트(``core.policy_context``)의
``as_of`` 와 ``include_proposed`` 에 따라 버전을 고른다.

- 시점 지정 없음: 확정(enacted) 버전 중 시행일이 가장 늦은 것. 호출 시각에 의존하지 않아 결정적이다.
- ``as_of`` 지정: 시행 기간 [effective_date, effective_to] 에 시점이 속하는 버전 중 시행일이 가장 늦은 것.
  교체되어 지난 버전(superseded)도 자기 기간의 시점에는 쓰인다.
- 개정안(proposed) 버전은 ``include_proposed`` 일 때만 후보이며 결과에 법적 상태가 표기된다.

같은 파일 이름이 두 저장소에 있으면 덮어쓰기(override)가 패키지보다 우선한다.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from sootool.core.errors import (
    InvalidInputError,
    PolicyFormatError,
    PolicyNotEnactedError,
    PolicyNotInEffectError,
)
from sootool.core.policy_context import POLICY_AS_OF, POLICY_INCLUDE_PROPOSED
from sootool.policies import (
    PolicyIntegrityError,
    UnsupportedPolicyError,
    _compute_sha256,
    _find_supported_years,
)
from sootool.policy_mgmt.paths import (
    get_override_policy_dir,
    get_package_policy_dir,
    safe_component,
)

log = logging.getLogger("sootool.policy_mgmt.loader")

STATUS_ENACTED    = "enacted"
STATUS_PROPOSED   = "proposed"
STATUS_SUPERSEDED = "superseded"
VALID_STATUSES    = (STATUS_ENACTED, STATUS_PROPOSED, STATUS_SUPERSEDED)

_REQUIRED_FIELDS = ("sha256", "effective_date", "notice_no", "source_url", "data")


@dataclass(frozen=True)
class _Version:
    path:           Path
    source:         str
    status:         str
    effective_from: date
    effective_to:   date | None
    loaded:         dict[str, Any]

    def contains(self, day: date) -> bool:
        return self.effective_from <= day and (self.effective_to is None or day <= self.effective_to)

    def period(self) -> dict[str, Any]:
        return {
            "effective_from": self.effective_from.isoformat(),
            "effective_to":   self.effective_to.isoformat() if self.effective_to else None,
            "status":         self.status,
        }


# Module-level cache: keyed by (domain, key, year) -> every version of that policy year.
# Access guarded by _CACHE_LOCK
_CACHE: dict[tuple[str, str, int], list[_Version]] = {}
_CACHE_LOCK = threading.Lock()

_SHA256_LINE_RE_LOADER = re.compile(r"^sha256:.*\n", re.MULTILINE)


def _as_date(value: Any, field: str, yaml_path: Path) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise PolicyFormatError(f"Policy YAML field '{field}' is not an ISO date: {value!r} ({yaml_path})") from exc


def _parse_dates_and_status(doc: dict[str, Any], yaml_path: Path) -> tuple[str, date, date | None]:
    status = str(doc.get("status", STATUS_ENACTED))
    if status not in VALID_STATUSES:
        raise PolicyFormatError(
            f"Policy YAML field 'status' must be one of {list(VALID_STATUSES)}: {status!r} ({yaml_path})"
        )
    effective_from = _as_date(doc["effective_date"], "effective_date", yaml_path)
    raw_to         = doc.get("effective_to")
    effective_to   = _as_date(raw_to, "effective_to", yaml_path) if raw_to not in (None, "") else None
    if effective_to is not None and effective_to < effective_from:
        raise PolicyFormatError(f"Policy YAML 'effective_to' precedes 'effective_date': {yaml_path}")
    return status, effective_from, effective_to


def _load_yaml_file(yaml_path: Path, source: str) -> dict[str, Any]:
    """Load, validate, and SHA256-verify a policy YAML file.

    Returns a dict with keys: data, policy_version, source.
    """
    raw_text = yaml_path.read_text(encoding="utf-8")
    doc = yaml.safe_load(raw_text)

    for field in _REQUIRED_FIELDS:
        if field not in doc:
            raise PolicyFormatError(f"Policy YAML missing required field '{field}': {yaml_path}")

    declared_sha256 = doc["sha256"]
    actual_sha256 = _compute_sha256(raw_text)

    if actual_sha256 != declared_sha256:
        raise PolicyIntegrityError(yaml_path, declared_sha256, actual_sha256)

    status, effective_from, effective_to = _parse_dates_and_status(doc, yaml_path)

    return {
        "data": doc["data"],
        "policy_version": {
            "year":           _extract_year_from_doc(doc, yaml_path),
            "sha256":         declared_sha256,
            "effective_date": effective_from.isoformat(),
            "effective_to":   effective_to.isoformat() if effective_to else None,
            "status":         status,
            "version":        str(doc["version"]) if doc.get("version") is not None else None,
            "notice_no":      doc.get("notice_no", ""),
            "source_url":     doc.get("source_url", ""),
            "citations":      doc.get("citations", []),
            "reviewed_by":    doc.get("reviewed_by", []),
        },
        "source": source,
        "path":   str(yaml_path),
    }


def _extract_year_from_doc(doc: dict[str, Any], yaml_path: Path) -> int:
    """Extract year from doc['year'] if present, otherwise from filename."""
    if "year" in doc:
        return int(doc["year"])
    # Parse from filename pattern <name>_<year>.yaml or <name>_<year>@<date>.yaml
    parsed = parse_policy_filename(yaml_path.name)
    return parsed[1] if parsed else 0


def parse_policy_filename(filename: str) -> tuple[str, int, str | None] | None:
    """``<name>_<year>[@<시행일>].yaml`` 에서 (이름, 연도, 시행일 접미사)를 읽는다. 형식이 다르면 None."""
    if not filename.endswith(".yaml"):
        return None
    stem = filename[: -len(".yaml")]
    base, _, suffix = stem.partition("@")
    parts = base.rsplit("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return parts[0], int(parts[1]), (suffix or None)


def _record_policy_usage(
    result: dict[str, Any],
    domain: str,
    key: str,
    year: int,
) -> None:
    """Publish the loaded policy's sha256/source/legal status to the integrity context.

    Invoked on every successful load() call (cache hit or miss). The integrity
    post-processor reads this thread-local data to stamp ``policy_sha256``,
    ``policy_source`` and the legal status on the response's ``_meta.integrity`` block.
    """
    from sootool.core.audit import set_policy_meta  # local import avoids cycle

    pv     = result.get("policy_version", {})
    sha    = pv.get("sha256")
    source = result.get("source")
    set_policy_meta(
        source, sha, domain=domain, key=key, year=year,
        status=pv.get("status"),
        effective_from=pv.get("effective_date"),
        effective_to=pv.get("effective_to"),
    )


def _is_safe_key(domain: str, key: str) -> bool:
    """영역과 정책 이름이 저장소 경로로 쓸 수 있는 형식인지 반환한다."""
    try:
        safe_component(domain, "domain")
        safe_component(key, "key")
    except InvalidInputError:
        return False
    return True


def _discover(domain: str, key: str, year: int) -> list[_Version]:
    """두 저장소에서 (domain, key, year) 의 모든 버전 파일을 읽는다. 같은 파일 이름은 override 가 우선."""
    found: dict[str, tuple[Path, str]] = {}
    if not _is_safe_key(domain, key):
        return []
    for source, base in (("package", get_package_policy_dir()), ("override", get_override_policy_dir())):
        directory = base / domain
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(f"{key}_{year}*.yaml")):
            parsed = parse_policy_filename(path.name)
            if parsed is not None and parsed[0] == key and parsed[1] == year:
                found[path.name] = (path, source)

    versions: list[_Version] = []
    for name in sorted(found):
        path, source = found[name]
        loaded = _load_yaml_file(path, source=source)
        pv = loaded["policy_version"]
        versions.append(_Version(
            path=path,
            source=source,
            status=pv["status"],
            effective_from=date.fromisoformat(pv["effective_date"]),
            effective_to=date.fromisoformat(pv["effective_to"]) if pv["effective_to"] else None,
            loaded=loaded,
        ))
        log.debug("Policy %s/%s/%d version loaded from %s: %s", domain, key, year, source, path)
    return versions


def existing_versions(domain: str, key: str, year: int) -> list[dict[str, Any]]:
    """(domain, key, year) 의 기존 버전 파일 요약(파일 이름, 저장소, 상태, 시행 기간)을 반환한다.

    캐시를 거치지 않고 저장소를 직접 읽는다. 관리 도구가 새 버전을 저장하기 전에 기존 버전과 겹치는지
    확인하는 용도다.
    """
    return [
        {"filename": v.path.name, "source": v.source, **v.period()}
        for v in _discover(domain, key, year)
    ]


def version_filename(domain: str, key: str, year: int, effective_date: str) -> str:
    """새 정책 문서를 저장할 파일 이름을 정한다.

    같은 연도에 기존 버전이 없으면 ``<key>_<year>.yaml``. 시행일이 같은 기존 버전이 있으면 그 파일 이름
    (교체). 시행일이 다른 새 버전이면 ``<key>_<year>@<시행일>.yaml``.
    """
    versions = _discover(domain, key, year)
    if not versions:
        return f"{key}_{year}.yaml"
    for version in versions:
        if version.effective_from.isoformat() == effective_date:
            return version.path.name
    return f"{key}_{year}@{effective_date}.yaml"


def _unsupported(domain: str, key: str, year: int) -> UnsupportedPolicyError:
    supported: set[int] = set()
    for base in (get_package_policy_dir(), get_override_policy_dir()) if _is_safe_key(domain, key) else ():
        directory = base / domain
        if directory.exists():
            supported.update(_find_supported_years(directory, key))
    return UnsupportedPolicyError(domain, key, year, sorted(supported))


def _select(
    domain: str,
    key: str,
    year: int,
    versions: list[_Version],
    as_of: date | None,
    include_proposed: bool,
) -> _Version:
    if not versions:
        raise _unsupported(domain, key, year)

    usable = {STATUS_ENACTED, STATUS_SUPERSEDED} | ({STATUS_PROPOSED} if include_proposed else set())

    if as_of is None:
        pool = [v for v in versions if v.status in usable and v.status != STATUS_SUPERSEDED]
        if pool:
            return max(pool, key=lambda v: v.effective_from)
        if any(v.status == STATUS_PROPOSED for v in versions):
            raise PolicyNotEnactedError(domain, key, year)
        raise _unsupported(domain, key, year)

    pool = [v for v in versions if v.status in usable and v.contains(as_of)]
    if pool:
        return max(pool, key=lambda v: v.effective_from)
    if not include_proposed and any(v.status == STATUS_PROPOSED and v.contains(as_of) for v in versions):
        raise PolicyNotEnactedError(domain, key, year)
    raise PolicyNotInEffectError(
        domain, key, year, as_of.isoformat(),
        [v.period() for v in sorted(versions, key=lambda v: v.effective_from) if v.status in usable],
    )


def load(domain: str, key: str, year: int) -> dict[str, Any]:
    """Load policy with dual-store priority: override > package.

    Returns dict with keys: data, policy_version, source ("package" | "override").
    The version is chosen by the call's policy context (as_of, include_proposed).

    Raises UnsupportedPolicyError if neither store has the policy year,
    PolicyNotInEffectError / PolicyNotEnactedError when the context excludes every version.
    """
    cache_key = (domain, key, year)
    with _CACHE_LOCK:
        versions = _CACHE.get(cache_key)
    if versions is None:
        versions = _discover(domain, key, year)
        if versions:
            with _CACHE_LOCK:
                _CACHE[cache_key] = versions

    chosen = _select(domain, key, year, versions, POLICY_AS_OF.get(), POLICY_INCLUDE_PROPOSED.get())
    _record_policy_usage(chosen.loaded, domain, key, year)
    return chosen.loaded


def invalidate_cache(domain: str | None = None, key: str | None = None, year: int | None = None) -> None:
    """Invalidate loader cache entries matching the given criteria.

    Passing no arguments clears the entire cache.
    """
    with _CACHE_LOCK:
        if domain is None and key is None and year is None:
            _CACHE.clear()
            return
        to_remove = [
            k for k in _CACHE
            if (domain is None or k[0] == domain)
            and (key is None or k[1] == key)
            and (year is None or k[2] == year)
        ]
        for k in to_remove:
            del _CACHE[k]


def list_available_policies() -> list[dict[str, Any]]:
    """Return metadata for all discoverable policy version files in both stores."""
    entries: dict[tuple[str, str, int, str], dict[str, Any]] = {}

    _scan_store(get_package_policy_dir(), "package", entries)
    _scan_store(get_override_policy_dir(), "override", entries)

    return sorted(entries.values(), key=lambda e: (e["domain"], e["name"], e["year"], e["effective_date"]))


def _scan_store(
    base: Path,
    source: str,
    entries: dict[tuple[str, str, int, str], dict[str, Any]],
) -> None:
    if not base.exists():
        return
    for domain_dir in base.iterdir():
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        if domain.startswith("_"):
            continue
        for yaml_path in domain_dir.glob("*.yaml"):
            parsed = parse_policy_filename(yaml_path.name)
            if parsed is None:
                continue
            name, year, _suffix = parsed
            try:
                doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                effective_date = str(doc.get("effective_date", ""))
                key = (domain, name, year, yaml_path.name)
                entry = {
                    "domain":         domain,
                    "name":           name,
                    "year":           year,
                    "source":         source,
                    "sha256":         doc.get("sha256", ""),
                    "effective_date": effective_date,
                    "effective_to":   str(doc["effective_to"]) if doc.get("effective_to") else None,
                    "status":         str(doc.get("status", STATUS_ENACTED)),
                    "version":        str(doc["version"]) if doc.get("version") is not None else None,
                    "is_active":      source == "override" or key not in entries,
                    "is_override":    source == "override",
                    "path":           str(yaml_path),
                }
                if source == "override" or key not in entries:
                    # override always wins — replace any existing package entry of the same file
                    entries[key] = entry
            except Exception:
                log.warning("Could not read policy file: %s", yaml_path, exc_info=True)
