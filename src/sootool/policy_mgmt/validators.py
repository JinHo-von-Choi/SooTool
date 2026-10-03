"""6-stage validation pipeline for policy YAML content.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import date
from decimal import Decimal
from typing import Any

import yaml

from sootool.policy_mgmt.loader import VALID_STATUSES, existing_versions
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
    _stage2_header_v2(doc, findings)

    # Stage 3: Domain pydantic schema validation
    if name:
        _stage3_schema(doc, domain, name, findings)

    # Stage 4: Cross-field validation
    _stage4_cross_validation(doc, domain, findings)
    if name:
        _stage4_version_overlap(doc, domain, name, findings)

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


def _iso_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _stage2_header_v2(doc: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    """정책 헤더 v2 필드(status, effective_to, citations, reviewed_by) 검증."""

    def finding(level: str, path: str, message: str) -> None:
        findings.append({"level": level, "path": path, "message": message, "stage": 2})

    status = doc.get("status", "enacted")
    if status not in VALID_STATUSES:
        finding("error", "status", f"status must be one of {list(VALID_STATUSES)}, got {status!r}")

    effective_from = _iso_date(doc["effective_date"]) if "effective_date" in doc else None
    if "effective_date" in doc and effective_from is None:
        finding("error", "effective_date", f"effective_date must be an ISO date (YYYY-MM-DD), got {doc['effective_date']!r}")

    raw_to = doc.get("effective_to")
    if raw_to not in (None, ""):
        effective_to = _iso_date(raw_to)
        if effective_to is None:
            finding("error", "effective_to", f"effective_to must be an ISO date (YYYY-MM-DD), got {raw_to!r}")
        elif effective_from is not None and effective_to < effective_from:
            finding("error", "effective_to", "effective_to must not precede effective_date")

    citations = doc.get("citations")
    if citations is None or citations == []:
        # 개정안은 근거 조문(개정안 이름, 입법예고 번호 등)이 없으면 법적 효력과 출처를 확인할 수 없다.
        level = "error" if status == "proposed" else "warning"
        finding(level, "citations", "citations (law and article references) are missing")
    elif not isinstance(citations, list):
        finding("error", "citations", "citations must be a list of {law, article?, url?, note?} mappings")
    else:
        for index, citation in enumerate(citations):
            if not isinstance(citation, dict) or not str(citation.get("law", "")).strip():
                finding("error", f"citations[{index}]", "each citation must be a mapping with a non-empty 'law'")
                continue
            unknown = set(citation) - {"law", "article", "url", "note"}
            if unknown:
                finding("error", f"citations[{index}]", f"unknown citation fields: {sorted(unknown)}")

    reviewed_by = doc.get("reviewed_by")
    if reviewed_by is not None and (
        not isinstance(reviewed_by, list) or not all(isinstance(r, str) and r.strip() for r in reviewed_by)
    ):
        finding("error", "reviewed_by", "reviewed_by must be a list of non-empty strings")


def _stage4_version_overlap(
    doc: dict[str, Any],
    domain: str,
    name: str,
    findings: list[dict[str, Any]],
) -> None:
    """같은 연도의 확정 버전끼리 시행 기간이 겹치지 않는지 확인한다.

    같은 시행일의 기존 버전은 교체되므로 비교에서 제외하고, 개정안(proposed)은 확정 버전과 겹칠 수 있다.
    """
    effective_from = _iso_date(doc.get("effective_date"))
    if effective_from is None or doc.get("status", "enacted") != "enacted":
        return
    effective_to = _iso_date(doc.get("effective_to")) if doc.get("effective_to") not in (None, "") else None
    year = int(doc["year"]) if str(doc.get("year", "")).isdigit() else effective_from.year

    for version in existing_versions(domain, name, year):
        if version["status"] != "enacted" or version["effective_from"] == effective_from.isoformat():
            continue
        other_from = date.fromisoformat(version["effective_from"])
        other_to   = date.fromisoformat(version["effective_to"]) if version["effective_to"] else None
        starts_before_other_ends = other_to is None or effective_from <= other_to
        ends_after_other_starts  = effective_to is None or other_from <= effective_to
        if starts_before_other_ends and ends_after_other_starts:
            findings.append({
                "level":   "error",
                "path":    "effective_date",
                "message": (
                    f"effective period overlaps the enacted version {version['filename']} "
                    f"({version['effective_from']}~{version['effective_to'] or 'open'}); "
                    "close the earlier version with effective_to first"
                ),
                "stage":   4,
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
    for label, table in _extract_bracket_tables(data).items():
        _validate_brackets_cross(table, findings, label)

    # Rate range check for scalar rates
    _validate_scalar_rates(data, findings)


_BRACKET_SOURCES = ("brackets", "income_tax_brackets", "ltcg_brackets")


def _extract_bracket_tables(data: dict[str, Any]) -> dict[str, list[Any]]:
    """data 안의 구간표를 이름별로 모은다. 신고 유형별 표(dict of list)는 ``이름.신고유형`` 으로 펼친다."""
    sources: list[tuple[str, Any]] = [(key, data.get(key)) for key in _BRACKET_SOURCES]
    house = data.get("house")
    if isinstance(house, dict):
        sources.append(("house.brackets", house.get("brackets")))

    tables: dict[str, list[Any]] = {}
    for label, raw in sources:
        if isinstance(raw, list):
            tables[label] = list(raw)
        elif isinstance(raw, dict):
            for key, table in raw.items():
                if isinstance(table, list):
                    tables[f"{label}.{key}"] = list(table)
    return tables


def _validate_brackets_cross(
    brackets: list[Any],
    findings: list[dict[str, Any]],
    label:    str = "brackets",
) -> None:
    if not all(isinstance(b, dict) for b in brackets):
        findings.append({
            "level":   "error",
            "path":    label,
            "message": "Every bracket entry must be a mapping with 'upper' and 'rate'",
            "stage":   4,
        })
        return
    for i, b in enumerate(brackets[:-1]):
        upper = b.get("upper")
        if upper is None:
            findings.append({
                "level":   "error",
                "path":    f"{label}[{i}].upper",
                "message": "Only the last bracket may have upper=None",
                "stage":   4,
            })

    if brackets and brackets[-1].get("upper") is not None:
        findings.append({
            "level":   "error",
            "path":    f"{label}[{len(brackets)-1}].upper",
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
                        "path":    f"{label}[{i+1}].upper",
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
                        "path":    f"{label}[{i}].rate",
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
    new_tables = _extract_bracket_tables(doc.get("data", {}))
    old_tables = _extract_bracket_tables(prev_data)

    for label, new_brackets in new_tables.items():
        old_brackets = old_tables.get(label)
        if old_brackets is None:
            continue
        if not all(isinstance(b, dict) for b in (*old_brackets, *new_brackets)):
            continue
        _compare_bracket_rates(label, old_brackets, new_brackets, threshold, findings)


def _compare_bracket_rates(
    label:        str,
    old_brackets: list[dict[str, Any]],
    new_brackets: list[dict[str, Any]],
    threshold:    float,
    findings:     list[dict[str, Any]],
) -> None:
    old_map = {str(b.get("upper")): Decimal(str(b.get("rate", 0))) for b in old_brackets}
    new_map = {str(b.get("upper")): Decimal(str(b.get("rate", 0))) for b in new_brackets}

    for upper_key, new_rate in new_map.items():
        if upper_key in old_map:
            old_rate = old_map[upper_key]
            delta = abs(new_rate - old_rate)
            if delta > Decimal(str(threshold)):
                findings.append({
                    "level":   "warning",
                    "path":    f"data.{label}[upper={upper_key}].rate",
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
