"""형식이 잘못된 정책 YAML 은 예외 없이 검증 오류로 보고된다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import pytest

from sootool import server
from sootool.core.registry import REGISTRY


@pytest.fixture
def admin(monkeypatch, tmp_path):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    server._load_modules()


@pytest.mark.parametrize("content", [
    "data: 1\n",
    "data: [1, 2]\n",
    "- a\n- b\n",
    "just text",
    "data:\n  brackets: 5\n",
    "data:\n  brackets:\n    - 1\n    - 2\n",
])
def test_propose_reports_malformed_documents_as_errors(admin, content):
    result = REGISTRY.invoke(
        "sootool.policy_propose", domain="tax", name="kr_income", year=2027, yaml_content=content,
    )
    assert result["validation"]["status"] == "error"


def test_validate_reports_malformed_data_as_errors(admin):
    result = REGISTRY.invoke("sootool.policy_validate", domain="tax", name="kr_income", yaml_content="data: 1\n")
    assert result["status"] == "error"
