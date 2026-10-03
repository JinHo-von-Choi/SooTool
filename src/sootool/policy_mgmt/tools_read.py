"""정책 조회 도구: list, get, history, diff, validate, export.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyVersion
from sootool.policy_mgmt import audit, drafts, loader
from sootool.policy_mgmt.diff import diff_policies
from sootool.policy_mgmt.tool_types import (
    PolicyBundle,
    PolicyDiffResult,
    PolicyExportResult,
    PolicyGetResult,
    PolicyHistoryResult,
    PolicyListResult,
    PolicyValidateResult,
)
from sootool.policy_mgmt.validators import validate_policy


@REGISTRY.tool(
    namespace="sootool",
    name="policy_list",
    description=(
        "패키지와 덮어쓰기 저장소의 모든 정책 파일 목록을 반환한다. 항목마다 영역, 이름, 연도, 출처(package 또는 override), "
        "시행일, 종료일, 상태, sha256 이 있다. 인자가 없고 읽기 전용이며, 정책 내용이 필요하면 sootool.policy_get 을 쓴다."
    ),
    version="1.0.0",
)
def policy_list() -> PolicyListResult:
    """Return metadata list for all known policy files."""
    policies = loader.list_available_policies()
    return cast(PolicyListResult, {"policies": policies, "count": len(policies)})


@REGISTRY.tool(
    namespace="sootool",
    name="policy_get",
    description=(
        "정책 파일 하나의 내용(data)과 출처(package 또는 override), 버전 정보를 반환한다. domain, name, year 로 지정하고 "
        "as_of(YYYY-MM-DD)로 그날 시행 중인 버전을, include_proposed 로 확정 전 개정안까지 고를 수 있다. "
        "존재하지 않는 연도를 지정하면 오류가 난다."
    ),
    version="1.0.0",
    policy=True,
)
def policy_get(domain: str, name: str, year: int) -> PolicyGetResult:
    """Load a specific policy by domain/name/year."""
    doc = loader.load(domain, name, year)
    return {
        "domain":   domain,
        "name":     name,
        "year":     year,
        "source":   doc.get("source", "package"),
        "data":     doc.get("data"),
        "policy_version": cast(PolicyVersion, doc.get("policy_version")),
    }


@REGISTRY.tool(
    namespace="sootool",
    name="policy_history",
    description=(
        "정책 하나(domain, name)의 변경 감사 기록을 기록된 순서대로 반환한다. 항목마다 action(activate, rollback, import), "
        "시각, audit_id, 변경 전후 sha256 이 있고 기록이 없으면 빈 목록이다. 정책 내용 자체는 sootool.policy_get 으로 본다."
    ),
    version="1.0.0",
)
def policy_history(domain: str, name: str) -> PolicyHistoryResult:
    """Return audit history for a given domain/name combination."""
    entries = audit.read_entries(domain=domain, name=name)
    return cast(PolicyHistoryResult, {"domain": domain, "name": name, "entries": entries, "count": len(entries)})


@REGISTRY.tool(
    namespace="sootool",
    name="policy_diff",
    description=(
        "정책 두 버전의 구간별 세율과 주요 값 변경을 비교한다. year_from 과 year_to 로 연도 간 비교하거나 draft_id 로 "
        "초안과 현재 시행본을 비교한다. 인자가 모자라거나 비교할 시행본이 없으면 error 필드로 알린다. 변경 이력은 sootool.policy_history 를 쓴다."
    ),
    version="1.0.0",
)
def policy_diff(
    domain:     str,
    name:       str,
    year_from:  int | None = None,
    year_to:    int | None = None,
    draft_id:   str | None = None,
) -> PolicyDiffResult:
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

        return cast(PolicyDiffResult, diff_policies(
            {"data": old_data}, {"data": new_data}, old_year, new_year
        ))

    if year_from is None or year_to is None:
        return {"error": "Provide year_from and year_to, or draft_id"}

    old_doc = loader.load(domain, name, year_from)
    new_doc = loader.load(domain, name, year_to)
    return cast(PolicyDiffResult, diff_policies(old_doc, new_doc, year_from, year_to))


@REGISTRY.tool(
    namespace="sootool",
    name="policy_validate",
    description=(
        "정책 YAML 문자열을 검증해 보고서(status, findings, sha256)를 반환한다. name 을 주면 도메인 스키마까지 검사하고 "
        "파일은 저장하지 않는다. auto_fix_sha256 이 참이면 계산한 해시를 fixed_sha256 으로 알려 준다. "
        "실제 반영은 sootool.policy_propose 와 sootool.policy_activate 를 쓴다."
    ),
    version="1.0.0",
)
def policy_validate(
    yaml_content:         str,
    domain:               str,
    name:                 str | None = None,
    sensitivity_threshold: float | None = None,
    auto_fix_sha256:      bool = False,
) -> PolicyValidateResult:
    """Run the 6-stage validation pipeline on the provided YAML string."""
    return cast(PolicyValidateResult, validate_policy(
        yaml_content=yaml_content,
        domain=domain,
        name=name,
        sensitivity_threshold=sensitivity_threshold,
        auto_fix_sha256=auto_fix_sha256,
    ))


@REGISTRY.tool(
    namespace="sootool",
    name="policy_export",
    description=(
        "정책 하나를 이식 가능한 묶음(원본 YAML과 메타데이터)으로 내보낸다. domain, name, year 로 지정하고 as_of, "
        "include_proposed 로 버전을 고른다. include_signature 가 참이고 private_key_b64 가 있으면 ed25519 서명을 붙인다. "
        "묶음은 sootool.policy_import 가 받는다."
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
) -> PolicyExportResult:
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

    bundle = cast(PolicyBundle, {
        "yaml_content": yaml_content,
        "metadata":     metadata,
    })

    if include_signature and private_key_b64:
        from sootool.policy_mgmt.signatures import bundle_payload_bytes, sign_bundle
        payload = bundle_payload_bytes(yaml_content, metadata)
        sig = sign_bundle(payload, private_key_b64)
        bundle["signature"] = sig

    return {"bundle": bundle}
