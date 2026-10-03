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
