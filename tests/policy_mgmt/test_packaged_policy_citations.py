"""패키지에 들어 있는 모든 정책 문서는 구조화된 근거 조문을 가진다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_POLICY_FILES = sorted((Path(__file__).resolve().parents[2] / "src" / "sootool" / "policies").glob("*/*.yaml"))


@pytest.mark.parametrize("path", _POLICY_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_policy_has_structured_citations(path):
    doc       = yaml.safe_load(path.read_text(encoding="utf-8"))
    citations = doc.get("citations")
    assert citations, "citations 가 비어 있다"
    for citation in citations:
        assert isinstance(citation, dict) and citation.get("law"), citation
        assert citation.get("article") or citation.get("note"), f"조문 또는 비고가 없다: {citation}"


def test_policy_files_were_found():
    assert len(_POLICY_FILES) >= 50


@pytest.mark.parametrize("path", _POLICY_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_policy_passes_structural_validation(path):
    """모든 패키지 정책이 영역별 구조 스키마와 공통 검증을 통과한다."""
    import re

    from sootool.policy_mgmt.schemas import get_domain_schema
    from sootool.policy_mgmt.validators import validate_policy

    domain = path.parent.name
    name   = re.sub(r"_\d{4}(@.*)?$", "", path.stem)
    assert get_domain_schema(domain, name) is not None, f"{domain}/{name} 구조 스키마가 등록되지 않았다"
    report = validate_policy(yaml_content=path.read_text(encoding="utf-8"), domain=domain, name=name)
    errors = [f for f in report["findings"] if f["level"] == "error"]
    assert not errors, errors


def test_structural_schema_rejects_a_policy_missing_a_required_key():
    from sootool.policy_mgmt.validators import validate_policy

    path = next(p for p in _POLICY_FILES if p.name == "kr_eitc_2026.yaml")
    doc  = yaml.safe_load(path.read_text(encoding="utf-8"))
    removed = sorted(doc["data"])[0]
    del doc["data"][removed]
    report = validate_policy(yaml_content=yaml.safe_dump(doc, allow_unicode=True), domain="tax", name="kr_eitc")
    assert any(f["level"] == "error" and removed in f["path"] + f["message"] for f in report["findings"]), report["findings"]
