"""
policies/__init__.py — Policy YAML loader with SHA256 integrity verification.

SHA256 Integrity Scheme:
  The sha256 field in each YAML file is computed over the file content
  with the `sha256: "..."` line STRIPPED (removed via regex before hashing).
  This allows the hash to be embedded in the file itself without circularity.

  Verification algorithm:
    1. Read raw file bytes (UTF-8).
    2. Remove the line matching /^sha256:.*\n/ from the content.
    3. Compute SHA256 of the stripped content.
    4. Compare to the declared sha256 field parsed from YAML.
    5. Mismatch -> PolicyIntegrityError.

Path resolution:
  {_POLICIES_DIR}/{domain}/{key}_{year}.yaml

Cache:
  load() is decorated with @functools.lru_cache so repeated calls return the
  same dict object. The cache is keyed by (domain, key, year).
  To invalidate (e.g., in tests), call load.cache_clear().

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import functools
import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

# Absolute path to the policies data directory (alongside this __init__.py)
_POLICIES_DIR: Path = Path(__file__).parent

_SHA256_LINE_RE = re.compile(r"^sha256:.*\n", re.MULTILINE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PolicyIntegrityError(Exception):
    """Raised when a policy YAML file's actual SHA256 does not match its declaration."""

    def __init__(self, path: Path, declared: str, actual: str) -> None:
        self.path      = path
        self.declared  = declared
        self.actual    = actual
        super().__init__(
            f"Policy integrity check failed for {path}: "
            f"declared={declared!r}, actual={actual!r}"
        )


class UnsupportedPolicyError(Exception):
    """Raised when no YAML file exists for the requested (domain, key, year)."""

    def __init__(
        self,
        domain:          str,
        key:             str,
        year:            int,
        supported_years: list[int],
    ) -> None:
        self.domain          = domain
        self.key             = key
        self.year            = year
        self.supported_years = supported_years
        super().__init__(
            f"Policy '{domain}/{key}' is not available for year {year}. "
            f"Supported years: {supported_years}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_sha256(raw_text: str) -> str:
    """Compute SHA256 of raw_text with the sha256 declaration line stripped."""
    stripped = _SHA256_LINE_RE.sub("", raw_text)
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def _find_supported_years(domain_dir: Path, key: str) -> list[int]:
    """Scan domain_dir for files matching {key}_YYYY.yaml and return sorted years."""
    pattern = f"{key}_*.yaml"
    years   = []
    for f in domain_dir.glob(pattern):
        stem = f.stem          # e.g. "kr_income_2026"
        suffix = stem[len(key) + 1:]   # e.g. "2026"
        if suffix.isdigit():
            years.append(int(suffix))
    return sorted(years)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@functools.cache
def load(domain: str, key: str, year: int) -> dict[str, Any]:
    """
    Load and verify a policy YAML file, returning an immutable-safe dict.

    Parameters
    ----------
    domain : str — policy domain subdirectory (e.g. "tax").
    key    : str — policy key prefix (e.g. "kr_income").
    year   : int — policy year (e.g. 2026).

    Returns
    -------
    dict with keys:
      - data         : dict  — the policy data section.
      - policy_version : dict — {year, sha256, effective_date, notice_no}.

    Raises
    ------
    UnsupportedPolicyError : if the file for the requested year does not exist.
    PolicyIntegrityError   : if the file's SHA256 does not match its declaration.
    """
    domain_dir = _POLICIES_DIR / domain
    yaml_path  = domain_dir / f"{key}_{year}.yaml"

    if not yaml_path.exists():
        # Scan for available years
        if domain_dir.exists():
            supported = _find_supported_years(domain_dir, key)
        else:
            supported = []
        raise UnsupportedPolicyError(domain, key, year, supported)

    raw_text = yaml_path.read_text(encoding="utf-8")
    doc      = yaml.safe_load(raw_text)

    # Verify required header fields
    for field in ("sha256", "effective_date", "notice_no", "source_url", "data"):
        if field not in doc:
            raise ValueError(f"Policy YAML missing required field '{field}': {yaml_path}")

    declared_sha256 = doc["sha256"]
    actual_sha256   = _compute_sha256(raw_text)

    if actual_sha256 != declared_sha256:
        raise PolicyIntegrityError(yaml_path, declared_sha256, actual_sha256)

    return {
        "data": doc["data"],
        "policy_version": {
            "year":           year,
            "sha256":         declared_sha256,
            "effective_date": doc["effective_date"],
            "notice_no":      doc["notice_no"],
        },
    }
