"""정책 쓰기 도구(관리자): propose, activate, rollback, import.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from sootool.core.registry import REGISTRY
from sootool.policy_mgmt import audit, drafts, loader
from sootool.policy_mgmt._tool_common import (
    _atomic_write_yaml,
    _existing_sha256,
    _new_audit_id,
    _require_admin,
    _target_path,
    log,
)
from sootool.policy_mgmt.diff import diff_policies
from sootool.policy_mgmt.paths import (
    get_override_policy_dir,
)
from sootool.policy_mgmt.validators import validate_policy


@REGISTRY.tool(
    namespace="sootool",
    name="policy_propose",
    description=(
        "[Admin] Create a draft policy. Returns validation report + year-over-year diff. "
        "Draft is not yet activated."
    ),
    version="1.0.0",
    read_only=False,
    idempotent=False,
)
def policy_propose(
    domain:               str,
    name:                 str,
    year:                 int,
    yaml_content:         str,
    source_url:           str = "",
    notice_no:            str = "",
    effective_date:       str = "",
    sensitivity_threshold: float | None = None,
    auto_fix_sha256:      bool = False,
    draft_id:             str | None = None,
) -> dict[str, Any]:
    """Save a policy draft after running the validation pipeline."""
    err = _require_admin()
    if err:
        return err

    # Load previous year data for YoY diff if available
    prev_data = None
    try:
        prev_doc = loader.load(domain, name, year - 1)
        prev_data = prev_doc.get("data")
    except Exception:
        log.debug("No previous year policy for %s/%s/%d", domain, name, year - 1)

    report = validate_policy(
        yaml_content=yaml_content,
        domain=domain,
        name=name,
        sensitivity_threshold=sensitivity_threshold,
        prev_year_data=prev_data,
        auto_fix_sha256=auto_fix_sha256,
    )

    # If auto_fix_sha256 and sha256 mismatch, substitute the correct sha256 in content
    effective_yaml = yaml_content
    if auto_fix_sha256 and report.get("fixed_sha256"):
        import re
        fixed_sha = report["fixed_sha256"]
        effective_yaml = re.sub(
            r'^sha256:.*$',
            f'sha256: "{fixed_sha}"',
            yaml_content,
            flags=re.MULTILINE,
        )

    meta = drafts.save_draft(
        domain=domain,
        name=name,
        year=year,
        yaml_content=effective_yaml,
        validation_report=report,
        source_url=source_url,
        notice_no=notice_no,
        effective_date=effective_date,
        draft_id=draft_id,
    )

    # Compute YoY diff
    diff_result = None
    if prev_data is not None:
        doc_new = yaml.safe_load(effective_yaml)
        new_data = doc_new.get("data", {}) if isinstance(doc_new, dict) else {}
        diff_result = diff_policies({"data": prev_data}, {"data": new_data}, year - 1, year)

    return {
        "draft_id":   meta["draft_id"],
        "domain":     domain,
        "name":       name,
        "year":       year,
        "validation": report,
        "diff":       diff_result,
        "expires_at": meta["expires_at"],
    }


@REGISTRY.tool(
    namespace="sootool",
    name="policy_activate",
    description=(
        "[Admin] Promote a draft to the override store, invalidate cache, and record audit log."
    ),
    version="1.0.0",
    read_only=False,
    destructive=True,
    idempotent=False,
)
def policy_activate(draft_id: str) -> dict[str, Any]:
    """Activate a previously proposed draft."""
    err = _require_admin()
    if err:
        return err

    draft_meta = drafts.load_draft(draft_id)
    domain = draft_meta["domain"]
    name   = draft_meta["name"]
    year   = draft_meta["year"]
    yaml_content = draft_meta["yaml_content"]

    # Write to override directory atomically. A different effective date makes a new version file.
    override_path = _target_path(domain, name, year, yaml_content)
    sha256_before = _existing_sha256(domain, override_path.name)
    _atomic_write_yaml(override_path, yaml_content)

    # Invalidate cache
    loader.invalidate_cache(domain=domain, key=name, year=year)

    # Determine sha256_after
    doc = yaml.safe_load(yaml_content)
    sha256_after = doc.get("sha256", "") if isinstance(doc, dict) else ""

    audit_id = _new_audit_id()
    entry = audit.make_entry(
        action="activate",
        domain=domain,
        name=name,
        year=year,
        audit_id=audit_id,
        draft_id=draft_id,
        sha256_before=sha256_before,
        sha256_after=sha256_after,
        source_url=draft_meta.get("source_url"),
        notice_no=draft_meta.get("notice_no"),
        validation=draft_meta.get("validation"),
    )
    audit.append_entry(entry)

    # Delete the draft
    drafts.delete_draft(draft_id)

    return {
        "activated":  True,
        "domain":     domain,
        "name":       name,
        "year":       year,
        "source":     "override",
        "audit_id":   audit_id,
        "sha256":     sha256_after,
    }


@REGISTRY.tool(
    namespace="sootool",
    name="policy_rollback",
    description=(
        "[Admin] Remove the override file for a policy, reverting to the package default."
    ),
    version="1.0.0",
    read_only=False,
    destructive=True,
    idempotent=False,
)
def policy_rollback(domain: str, name: str, year: int, effective_date: str = "") -> dict[str, Any]:
    """Remove the override version for domain/name/year, reverting to the package default.

    A year may have several override versions (different effective dates). Pass
    ``effective_date`` (YYYY-MM-DD) to pick one; without it the single override is removed and
    several overrides are reported as ambiguous.
    """
    err = _require_admin()
    if err:
        return err

    override_dir = get_override_policy_dir() / domain
    candidates: list[tuple[Path, str]] = []
    if override_dir.is_dir():
        for path in sorted(override_dir.glob(f"{name}_{year}*.yaml")):
            parsed = loader.parse_policy_filename(path.name)
            if parsed is None or parsed[0] != name or parsed[1] != year:
                continue
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:
                doc = None
            effective = str(doc.get("effective_date", "")) if isinstance(doc, dict) else ""
            candidates.append((path, effective))

    if effective_date:
        candidates = [(p, e) for p, e in candidates if e == effective_date]
    elif len(candidates) > 1:
        return {
            "error":    "ambiguous_version",
            "message":  "Several override versions exist; pass effective_date to choose one.",
            "versions": [e for _, e in candidates],
        }

    sha256_before = None
    removed = False
    if candidates:
        override_path = candidates[0][0]
        try:
            doc = yaml.safe_load(override_path.read_text(encoding="utf-8"))
            sha256_before = doc.get("sha256", "") if isinstance(doc, dict) else ""
        except Exception:
            log.debug("Could not read sha256 from override before rollback", exc_info=True)
        override_path.unlink()
        loader.invalidate_cache(domain=domain, key=name, year=year)
        removed = True

    audit_id = _new_audit_id()
    entry = audit.make_entry(
        action="rollback",
        domain=domain,
        name=name,
        year=year,
        audit_id=audit_id,
        sha256_before=sha256_before,
        sha256_after=None,
    )
    audit.append_entry(entry)

    return {
        "rolled_back": removed,
        "domain":      domain,
        "name":        name,
        "year":        year,
        "audit_id":    audit_id,
        "message": (
            "Override removed; reverting to package default."
            if removed
            else "No override found; nothing to roll back."
        ),
    }


@REGISTRY.tool(
    namespace="sootool",
    name="policy_import",
    description=(
        "[Admin] Import an external policy bundle into the override store. "
        "Optional ed25519 signature verification."
    ),
    version="1.0.0",
    read_only=False,
    destructive=True,
    idempotent=False,
)
def policy_import(
    bundle:             dict[str, Any],
    require_signature:  bool = False,
    public_key_b64:     str | None = None,
) -> dict[str, Any]:
    """Import a bundle exported by policy_export."""
    err = _require_admin()
    if err:
        return err

    # Check SOOTOOL_POLICY_REQUIRE_SIGNATURE env
    env_require_sig = os.environ.get("SOOTOOL_POLICY_REQUIRE_SIGNATURE", "").strip() in ("1", "true", "yes")
    if env_require_sig:
        require_signature = True

    yaml_content = bundle.get("yaml_content", "")
    metadata     = bundle.get("metadata", {})
    signature    = bundle.get("signature")

    if require_signature:
        if not signature:
            return {"error": "signature_required", "message": "Bundle signature is missing"}
        if not public_key_b64:
            return {"error": "signature_required", "message": "public_key_b64 is required for verification"}
        from sootool.policy_mgmt.signatures import (
            SignatureVerificationError,
            bundle_payload_bytes,
            verify_bundle,
        )
        payload = bundle_payload_bytes(yaml_content, metadata)
        try:
            verify_bundle(payload, signature, public_key_b64)
        except SignatureVerificationError as exc:
            return {"error": "signature_invalid", "message": str(exc)}

    domain = metadata.get("domain", "")
    name   = metadata.get("name", "")
    year   = metadata.get("year", 0)

    if not domain or not name or not year:
        return {"error": "invalid_bundle", "message": "Bundle metadata missing domain/name/year"}

    # Validate the YAML before writing
    report = validate_policy(yaml_content=yaml_content, domain=domain, name=name)
    if report["status"] == "error":
        return {
            "error":      "validation_failed",
            "validation": report,
        }

    # Write to override. A different effective date makes a new version file.
    override_path = _target_path(domain, name, year, yaml_content)
    sha256_before = _existing_sha256(domain, override_path.name)
    _atomic_write_yaml(override_path, yaml_content)
    loader.invalidate_cache(domain=domain, key=name, year=year)

    doc = yaml.safe_load(yaml_content)
    sha256_after = doc.get("sha256", "") if isinstance(doc, dict) else ""

    audit_id = _new_audit_id()
    entry = audit.make_entry(
        action="import",
        domain=domain,
        name=name,
        year=year,
        audit_id=audit_id,
        sha256_before=sha256_before,
        sha256_after=sha256_after,
        source_url=metadata.get("policy_version", {}).get("source_url", ""),
        notice_no=metadata.get("policy_version", {}).get("notice_no", ""),
        validation=report,
    )
    audit.append_entry(entry)

    return {
        "imported":  True,
        "domain":    domain,
        "name":      name,
        "year":      year,
        "audit_id":  audit_id,
        "sha256":    sha256_after,
        "validation": report,
    }
