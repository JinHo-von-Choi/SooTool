"""sootool.policy_* MCP tools — 10 policy management tools.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

import yaml

from sootool.core.registry import REGISTRY
from sootool.policy_mgmt import audit, drafts, loader
from sootool.policy_mgmt.diff import diff_policies
from sootool.policy_mgmt.paths import get_override_policy_dir
from sootool.policy_mgmt.validators import validate_policy

log = logging.getLogger("sootool.policy_mgmt.tools")

_ADMIN_REQUIRED_ERROR = {
    "error":   "admin_required",
    "message": (
        "This tool requires admin mode. Set SOOTOOL_ADMIN_MODE=1 "
        "or start the server with --admin."
    ),
}


def _is_admin() -> bool:
    return bool(os.environ.get("SOOTOOL_ADMIN_MODE", "").strip() in ("1", "true", "yes"))


def _require_admin() -> dict[str, Any] | None:
    if not _is_admin():
        return _ADMIN_REQUIRED_ERROR
    return None


def _new_audit_id() -> str:
    return f"aud-{uuid.uuid4().hex}"


def _atomic_write_yaml(yaml_path: Path, content: str) -> None:
    """Write content to yaml_path atomically via tmp -> fsync -> rename."""
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    # Enforce 0700 on directory
    try:
        os.chmod(yaml_path.parent, 0o700)
    except OSError:
        pass
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


# ---------------------------------------------------------------------------
# 1. policy_list
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_list",
    description="List all available policy files in both package and override stores.",
    version="1.0.0",
)
def policy_list() -> dict[str, Any]:
    """Return metadata list for all known policy files."""
    policies = loader.list_available_policies()
    return {"policies": policies, "count": len(policies)}


# ---------------------------------------------------------------------------
# 2. policy_get
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_get",
    description="Retrieve a policy file's content with source (package | override) indication.",
    version="1.0.0",
)
def policy_get(domain: str, name: str, year: int) -> dict[str, Any]:
    """Load a specific policy by domain/name/year."""
    doc = loader.load(domain, name, year)
    return {
        "domain":   domain,
        "name":     name,
        "year":     year,
        "source":   doc.get("source", "package"),
        "data":     doc.get("data"),
        "policy_version": doc.get("policy_version"),
    }


# ---------------------------------------------------------------------------
# 3. policy_history
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_history",
    description="Return time-ordered audit log entries for a policy.",
    version="1.0.0",
)
def policy_history(domain: str, name: str) -> dict[str, Any]:
    """Return audit history for a given domain/name combination."""
    entries = audit.read_entries(domain=domain, name=name)
    return {"domain": domain, "name": name, "entries": entries, "count": len(entries)}


# ---------------------------------------------------------------------------
# 4. policy_diff
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_diff",
    description=(
        "Semantic diff between two policy versions. "
        "Use year_from/year_to for cross-year, or draft_id with 'active' to compare draft vs live."
    ),
    version="1.0.0",
)
def policy_diff(
    domain:     str,
    name:       str,
    year_from:  int | None = None,
    year_to:    int | None = None,
    draft_id:   str | None = None,
) -> dict[str, Any]:
    """Compute a semantic diff between two policy versions."""
    if draft_id:
        # Compare draft vs currently active policy
        draft_meta = drafts.load_draft(draft_id)
        yaml_content = draft_meta["yaml_content"]
        doc_new = yaml.safe_load(yaml_content)
        new_data = doc_new.get("data", {})
        new_year = draft_meta.get("year", 0)

        try:
            active_doc = loader.load(domain, name, new_year)
            old_data = active_doc.get("data", {})
            old_year = new_year
        except Exception:
            return {"error": f"No active policy to compare against for {domain}/{name}/{new_year}"}

        return diff_policies(
            {"data": old_data}, {"data": new_data}, old_year, new_year
        )

    if year_from is None or year_to is None:
        return {"error": "Provide year_from and year_to, or draft_id"}

    old_doc = loader.load(domain, name, year_from)
    new_doc = loader.load(domain, name, year_to)
    return diff_policies(old_doc, new_doc, year_from, year_to)


# ---------------------------------------------------------------------------
# 5. policy_validate
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_validate",
    description=(
        "Validate YAML content against the domain schema and cross-validation rules. "
        "No writes performed."
    ),
    version="1.0.0",
)
def policy_validate(
    yaml_content:         str,
    domain:               str,
    name:                 str | None = None,
    sensitivity_threshold: float | None = None,
    auto_fix_sha256:      bool = False,
) -> dict[str, Any]:
    """Run the 6-stage validation pipeline on the provided YAML string."""
    return validate_policy(
        yaml_content=yaml_content,
        domain=domain,
        name=name,
        sensitivity_threshold=sensitivity_threshold,
        auto_fix_sha256=auto_fix_sha256,
    )


# ---------------------------------------------------------------------------
# 6. policy_propose (admin)
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_propose",
    description=(
        "[Admin] Create a draft policy. Returns validation report + year-over-year diff. "
        "Draft is not yet activated."
    ),
    version="1.0.0",
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


# ---------------------------------------------------------------------------
# 7. policy_activate (admin)
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_activate",
    description=(
        "[Admin] Promote a draft to the override store, invalidate cache, and record audit log."
    ),
    version="1.0.0",
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

    # Determine sha256_before (if override already exists)
    sha256_before = None
    try:
        existing = loader.load(domain, name, year)
        sha256_before = existing.get("policy_version", {}).get("sha256")
    except Exception:
        log.debug("No existing policy for %s/%s/%d (first activation)", domain, name, year)

    # Write to override directory atomically
    override_dir = get_override_policy_dir() / domain
    override_path = override_dir / f"{name}_{year}.yaml"
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


# ---------------------------------------------------------------------------
# 8. policy_rollback (admin)
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_rollback",
    description=(
        "[Admin] Remove the override file for a policy, reverting to the package default."
    ),
    version="1.0.0",
)
def policy_rollback(domain: str, name: str, year: int) -> dict[str, Any]:
    """Remove override for domain/name/year, reverting to the package default."""
    err = _require_admin()
    if err:
        return err

    override_path = get_override_policy_dir() / domain / f"{name}_{year}.yaml"

    sha256_before = None
    if override_path.exists():
        try:
            raw = override_path.read_text(encoding="utf-8")
            doc = yaml.safe_load(raw)
            sha256_before = doc.get("sha256", "") if isinstance(doc, dict) else ""
        except Exception:
            log.debug("Could not read sha256 from override before rollback", exc_info=True)
        override_path.unlink()
        loader.invalidate_cache(domain=domain, key=name, year=year)
        removed = True
    else:
        removed = False

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


# ---------------------------------------------------------------------------
# 9. policy_export
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_export",
    description="Export a policy as a portable bundle (YAML + metadata).",
    version="1.0.0",
)
def policy_export(
    domain:           str,
    name:             str,
    year:             int,
    include_signature: bool = False,
    private_key_b64:  str | None = None,
) -> dict[str, Any]:
    """Bundle a policy for sharing or import."""
    doc = loader.load(domain, name, year)

    # Read raw YAML from the source file
    source = doc.get("source", "package")
    if source == "override":
        yaml_path = get_override_policy_dir() / domain / f"{name}_{year}.yaml"
    else:
        from sootool.policy_mgmt.paths import get_package_policy_dir
        yaml_path = get_package_policy_dir() / domain / f"{name}_{year}.yaml"

    yaml_content = yaml_path.read_text(encoding="utf-8")

    metadata = {
        "domain":          domain,
        "name":            name,
        "year":            year,
        "source":          source,
        "policy_version":  doc.get("policy_version"),
    }

    bundle: dict[str, Any] = {
        "yaml_content": yaml_content,
        "metadata":     metadata,
    }

    if include_signature and private_key_b64:
        from sootool.policy_mgmt.signatures import bundle_payload_bytes, sign_bundle
        payload = bundle_payload_bytes(yaml_content, metadata)
        sig = sign_bundle(payload, private_key_b64)
        bundle["signature"] = sig

    return {"bundle": bundle}


# ---------------------------------------------------------------------------
# 10. policy_import (admin)
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="sootool",
    name="policy_import",
    description=(
        "[Admin] Import an external policy bundle into the override store. "
        "Optional ed25519 signature verification."
    ),
    version="1.0.0",
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

    # Determine sha256_before
    sha256_before = None
    try:
        existing = loader.load(domain, name, year)
        sha256_before = existing.get("policy_version", {}).get("sha256")
    except Exception:
        log.debug("No existing policy for %s/%s/%d (first import)", domain, name, year)

    # Write to override
    override_path = get_override_policy_dir() / domain / f"{name}_{year}.yaml"
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
