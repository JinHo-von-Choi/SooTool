"""정책 조회 도구: list, get, history, diff, validate, export.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sootool.core.registry import REGISTRY
from sootool.policy_mgmt import audit, drafts, loader
from sootool.policy_mgmt.diff import diff_policies
from sootool.policy_mgmt.validators import validate_policy


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


@REGISTRY.tool(
    namespace="sootool",
    name="policy_get",
    description=(
        "Retrieve a policy file's content with source (package | override) indication. "
        "as_of selects the version in effect on a date; include_proposed also considers unenacted drafts."
    ),
    version="1.0.0",
    policy=True,
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


@REGISTRY.tool(
    namespace="sootool",
    name="policy_export",
    description=(
        "Export a policy as a portable bundle (YAML + metadata). "
        "as_of selects the version in effect on a date; include_proposed also considers unenacted drafts."
    ),
    version="1.0.0",
    policy=True,
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

    # Read raw YAML from the file of the version the call resolved (as_of, include_proposed)
    source       = doc.get("source", "package")
    yaml_content = Path(doc["path"]).read_text(encoding="utf-8")

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
