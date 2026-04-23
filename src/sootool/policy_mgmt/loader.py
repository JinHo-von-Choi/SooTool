"""Dual-store policy loader — override directory takes priority over package defaults.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Any

import yaml

from sootool.policies import (
    PolicyIntegrityError,
    UnsupportedPolicyError,
    _compute_sha256,
    _find_supported_years,
)
from sootool.policy_mgmt.paths import get_override_policy_dir, get_package_policy_dir

log = logging.getLogger("sootool.policy_mgmt.loader")

# Module-level cache: keyed by (domain, key, year)
# Access guarded by _CACHE_LOCK
_CACHE: dict[tuple[str, str, int], dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()

_SHA256_LINE_RE_LOADER = re.compile(r"^sha256:.*\n", re.MULTILINE)


def _load_yaml_file(yaml_path: Path, source: str) -> dict[str, Any]:
    """Load, validate, and SHA256-verify a policy YAML file.

    Returns a dict with keys: data, policy_version, source.
    """
    raw_text = yaml_path.read_text(encoding="utf-8")
    doc = yaml.safe_load(raw_text)

    for field in ("sha256", "effective_date", "notice_no", "source_url", "data"):
        if field not in doc:
            raise ValueError(f"Policy YAML missing required field '{field}': {yaml_path}")

    declared_sha256 = doc["sha256"]
    actual_sha256 = _compute_sha256(raw_text)

    if actual_sha256 != declared_sha256:
        raise PolicyIntegrityError(yaml_path, declared_sha256, actual_sha256)

    return {
        "data": doc["data"],
        "policy_version": {
            "year":           _extract_year_from_doc(doc, yaml_path),
            "sha256":         declared_sha256,
            "effective_date": doc["effective_date"],
            "notice_no":      doc.get("notice_no", ""),
            "source_url":     doc.get("source_url", ""),
        },
        "source": source,
    }


def _extract_year_from_doc(doc: dict[str, Any], yaml_path: Path) -> int:
    """Extract year from doc['year'] if present, otherwise from filename."""
    if "year" in doc:
        return int(doc["year"])
    # Parse from filename pattern <name>_<year>.yaml
    stem = yaml_path.stem
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


def load(domain: str, key: str, year: int) -> dict[str, Any]:
    """Load policy with dual-store priority: override > package.

    Returns dict with keys: data, policy_version, source ("package" | "override").

    Raises UnsupportedPolicyError if neither store has the file.
    """
    cache_key = (domain, key, year)
    with _CACHE_LOCK:
        if cache_key in _CACHE:
            return _CACHE[cache_key]

    filename = f"{key}_{year}.yaml"

    # 1. Try override directory first
    override_dir = get_override_policy_dir() / domain
    override_path = override_dir / filename
    if override_path.exists():
        result = _load_yaml_file(override_path, source="override")
        log.debug("Policy %s/%s/%d loaded from override: %s", domain, key, year, override_path)
        with _CACHE_LOCK:
            _CACHE[cache_key] = result
        return result

    # 2. Fall back to package directory
    package_dir = get_package_policy_dir() / domain
    package_path = package_dir / filename
    if package_path.exists():
        result = _load_yaml_file(package_path, source="package")
        log.debug("Policy %s/%s/%d loaded from package: %s", domain, key, year, package_path)
        with _CACHE_LOCK:
            _CACHE[cache_key] = result
        return result

    # Neither found — collect supported years from both stores
    supported: list[int] = []
    if package_dir.exists():
        supported = _find_supported_years(package_dir, key)
    override_years: list[int] = []
    if override_dir.exists():
        override_years = _find_supported_years(override_dir, key)
    all_supported = sorted(set(supported) | set(override_years))
    raise UnsupportedPolicyError(domain, key, year, all_supported)


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
    """Return metadata for all discoverable policy files in both stores."""
    entries: dict[tuple[str, str, int], dict[str, Any]] = {}

    # Package store
    pkg_base = get_package_policy_dir()
    _scan_store(pkg_base, "package", entries)

    # Override store
    ovr_base = get_override_policy_dir()
    _scan_store(ovr_base, "override", entries)

    return sorted(entries.values(), key=lambda e: (e["domain"], e["name"], e["year"]))


def _scan_store(
    base: Path,
    source: str,
    entries: dict[tuple[str, str, int], dict[str, Any]],
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
            stem = yaml_path.stem
            parts = stem.rsplit("_", 1)
            if len(parts) != 2 or not parts[1].isdigit():
                continue
            name = parts[0]
            year = int(parts[1])
            key = (domain, name, year)

            try:
                raw_text = yaml_path.read_text(encoding="utf-8")
                doc = yaml.safe_load(raw_text)
                sha256_val = doc.get("sha256", "")
                effective_date = doc.get("effective_date", "")
                is_active = source == "override" or key not in entries
                entry = {
                    "domain":         domain,
                    "name":           name,
                    "year":           year,
                    "source":         source,
                    "sha256":         sha256_val,
                    "effective_date": effective_date,
                    "is_active":      is_active,
                    "is_override":    source == "override",
                    "path":           str(yaml_path),
                }
                if source == "override":
                    # override always wins — replace any existing package entry
                    entries[key] = entry
                elif key not in entries:
                    entries[key] = entry
            except Exception:
                log.warning("Could not read policy file: %s", yaml_path, exc_info=True)
