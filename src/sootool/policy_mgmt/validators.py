"""6-stage validation pipeline for policy YAML content.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from decimal import Decimal
from typing import Any

import yaml

from sootool.policy_mgmt.schemas import get_domain_schema

log = logging.getLogger("sootool.policy_mgmt.validators")

_SHA256_LINE_RE = re.compile(r"^sha256:.*\n", re.MULTILINE)


def _compute_sha256(raw_text: str) -> str:
    stripped = _SHA256_LINE_RE.sub("", raw_text)
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def validate_policy(
    yaml_content: str,
    domain: str,
    name: str | None = None,
    sensitivity_threshold: float | None = None,
    prev_year_data: dict[str, Any] | None = None,
    auto_fix_sha256: bool = False,
) -> dict[str, Any]:
    """Run the 6-stage validation pipeline.

    Returns a findings report dict:
        {status, findings, sha256, fixed_sha256 (if auto_fix)}
    """
    findings: list[dict[str, Any]] = []

    # Stage 1: Safe YAML parse
    doc = _stage1_yaml_parse(yaml_content, findings)
    if doc is None:
        return _build_report(findings, "")

    # Stage 2: Required metadata fields
    _stage2_required_fields(doc, findings)

    # Stage 3: Domain pydantic schema validation
    if name:
        _stage3_schema(doc, domain, name, findings)

    # Stage 4: Cross-field validation
    _stage4_cross_validation(doc, domain, findings)

    # Stage 5: YoY sensitivity check
    if prev_year_data is not None:
        threshold = _resolve_threshold(sensitivity_threshold)
        _stage5_sensitivity(doc, prev_year_data, threshold, findings)

    # Stage 6: SHA256 verification
    sha256_val = _stage6_sha256(yaml_content, doc, findings, auto_fix_sha256)

    report = _build_report(findings, sha256_val)
    if auto_fix_sha256:
        report["fixed_sha256"] = sha256_val
    return report


def _build_report(findings: list[dict[str, Any]], sha256_val: str) -> dict[str, Any]:
    errors   = [f for f in findings if f["level"] == "error"]
    warnings = [f for f in findings if f["level"] == "warning"]
    if errors:
        status = "error"
    elif warnings:
        status = "warning"
    else:
        status = "ok"
    return {
        "status":   status,
        "findings": findings,
        "sha256":   sha256_val,
    }


def _stage1_yaml_parse(
    yaml_content: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        doc = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        findings.append({
            "level":   "error",
            "path":    "",
            "message": f"YAML parse error: {exc}",
            "stage":   1,
        })
        return None

    if not isinstance(doc, dict):
        findings.append({
            "level":   "error",
            "path":    "",
            "message": "Top-level YAML must be a mapping (dict)",
            "stage":   1,
        })
        return None

    return doc


def _stage2_required_fields(
    doc: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    required = ("sha256", "effective_date", "notice_no", "source_url", "data")
    for field in required:
        if field not in doc:
            findings.append({
                "level":   "error",
                "path":    field,
                "message": f"Required field '{field}' is missing",
                "stage":   2,
            })


def _stage3_schema(
    doc: dict[str, Any],
    domain: str,
    name: str,
    findings: list[dict[str, Any]],
) -> None:
    schema_cls = get_domain_schema(domain, name)
    if schema_cls is None:
        findings.append({
            "level":   "info",
            "path":    "",
            "message": f"No domain schema registered for {domain}/{name}; skipping pydantic validation",
            "stage":   3,
        })
        return

    data = doc.get("data")
    if data is None:
        return

    try:
        schema_cls.model_validate(data)
    except Exception as exc:
        findings.append({
            "level":   "error",
            "path":    "data",
            "message": f"Schema validation failed: {exc}",
            "stage":   3,
        })


def _stage4_cross_validation(
    doc: dict[str, Any],
    domain: str,
    findings: list[dict[str, Any]],
) -> None:
    data = doc.get("data")
    if data is None:
        return

    # effective_date year vs year field consistency
    eff_date = doc.get("effective_date", "")
    doc_year = doc.get("year")
    if eff_date and doc_year:
        try:
            eff_year = int(str(eff_date)[:4])
            if eff_year != int(doc_year):
                findings.append({
                    "level":   "warning",
                    "path":    "effective_date",
                    "message": (
                        f"effective_date year ({eff_year}) does not match year field ({doc_year})"
                    ),
                    "stage":   4,
                })
        except (ValueError, TypeError):
            pass

    # Bracket cross-validation for tax domains
    brackets = _extract_brackets_from_data(data)
    if brackets:
        _validate_brackets_cross(brackets, findings)

    # Rate range check for scalar rates
    _validate_scalar_rates(data, findings)


def _extract_brackets_from_data(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    if "brackets" in data:
        return list(data["brackets"])
    if "income_tax_brackets" in data:
        return list(data["income_tax_brackets"])
    if "house" in data and isinstance(data["house"], dict) and "brackets" in data["house"]:
        return list(data["house"]["brackets"])
    return None


def _validate_brackets_cross(
    brackets: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    for i, b in enumerate(brackets[:-1]):
        upper = b.get("upper")
        if upper is None:
            findings.append({
                "level":   "error",
                "path":    f"brackets[{i}].upper",
                "message": "Only the last bracket may have upper=None",
                "stage":   4,
            })

    if brackets and brackets[-1].get("upper") is not None:
        findings.append({
            "level":   "error",
            "path":    f"brackets[{len(brackets)-1}].upper",
            "message": "Last bracket must have upper=None",
            "stage":   4,
        })

    uppers = [b.get("upper") for b in brackets[:-1]]
    for i in range(len(uppers) - 1):
        u1, u2 = uppers[i], uppers[i + 1]
        if u1 is not None and u2 is not None:
            try:
                if Decimal(str(u1)) >= Decimal(str(u2)):
                    findings.append({
                        "level":   "error",
                        "path":    f"brackets[{i+1}].upper",
                        "message": (
                            f"bracket upper values must be strictly increasing: "
                            f"index {i} ({u1}) >= index {i+1} ({u2})"
                        ),
                        "stage":   4,
                    })
            except Exception:
                log.debug("Could not compare bracket uppers at index %d", i, exc_info=True)

    for i, b in enumerate(brackets):
        rate = b.get("rate")
        if rate is not None:
            try:
                r = Decimal(str(rate))
                if not (Decimal("0") <= r <= Decimal("1")):
                    findings.append({
                        "level":   "error",
                        "path":    f"brackets[{i}].rate",
                        "message": f"rate must be 0 <= rate <= 1, got {r}",
                        "stage":   4,
                    })
            except Exception:
                log.debug("Could not validate bracket rate at index %d", i, exc_info=True)


def _validate_scalar_rates(
    data: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    rate_fields = ("dsr_cap",)
    for field in rate_fields:
        if field in data:
            try:
                r = Decimal(str(data[field]))
                if not (Decimal("0") <= r <= Decimal("1")):
                    findings.append({
                        "level":   "error",
                        "path":    field,
                        "message": f"{field} must be 0 <= value <= 1, got {r}",
                        "stage":   4,
                    })
            except Exception:
                log.debug("Could not validate scalar field %s", field, exc_info=True)


def _resolve_threshold(threshold: float | None) -> float:
    if threshold is not None:
        return threshold
    env = os.environ.get("SOOTOOL_POLICY_DIFF_THRESHOLD", "")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return 0.5


def _stage5_sensitivity(
    doc: dict[str, Any],
    prev_data: dict[str, Any],
    threshold: float,
    findings: list[dict[str, Any]],
) -> None:
    new_data = doc.get("data", {})
    new_brackets = _extract_brackets_from_data(new_data)
    old_brackets = _extract_brackets_from_data(prev_data)

    if new_brackets is None or old_brackets is None:
        return

    old_map = {str(b.get("upper")): Decimal(str(b.get("rate", 0))) for b in old_brackets}
    new_map = {str(b.get("upper")): Decimal(str(b.get("rate", 0))) for b in new_brackets}

    for upper_key, new_rate in new_map.items():
        if upper_key in old_map:
            old_rate = old_map[upper_key]
            delta = abs(new_rate - old_rate)
            if delta > Decimal(str(threshold)):
                findings.append({
                    "level":   "warning",
                    "path":    f"data.brackets[upper={upper_key}].rate",
                    "message": (
                        f"Rate change of {delta} exceeds sensitivity threshold {threshold}. "
                        f"Old: {old_rate}, New: {new_rate}. Possible typo."
                    ),
                    "stage":   5,
                })


def _stage6_sha256(
    yaml_content: str,
    doc: dict[str, Any],
    findings: list[dict[str, Any]],
    auto_fix: bool,
) -> str:
    computed = _compute_sha256(yaml_content)
    declared = doc.get("sha256", "")

    if computed != declared:
        if auto_fix:
            findings.append({
                "level":   "info",
                "path":    "sha256",
                "message": f"SHA256 auto-corrected from {declared!r} to {computed!r}",
                "stage":   6,
            })
        else:
            findings.append({
                "level":   "error",
                "path":    "sha256",
                "message": f"SHA256 mismatch: declared={declared!r}, computed={computed!r}",
                "stage":   6,
            })

    return computed
