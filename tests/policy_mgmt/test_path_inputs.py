"""정책 저장 경로에 쓰이는 입력(영역, 이름, 시행일, 초안 식별자)의 형식 검증 시험.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import pytest

from sootool import server
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policy_mgmt import drafts, loader
from sootool.policy_mgmt._tool_common import _target_path
from sootool.policy_mgmt.paths import safe_component, safe_id, safe_iso_date


@pytest.fixture
def admin(monkeypatch, tmp_path):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    server._load_modules()
    return tmp_path


@pytest.mark.parametrize("value", ["", "../x", "a/b", "a b", "a.b", "x" * 65, "한글", None, 3])
def test_safe_component_rejects_path_like_values(value):
    with pytest.raises(InvalidInputError):
        safe_component(value, "name")


@pytest.mark.parametrize("value", ["tax", "tax_us", "kr_income", "A1_b2"])
def test_safe_component_accepts_identifiers(value):
    assert safe_component(value, "name") == value


@pytest.mark.parametrize("value", ["../x", "2026-13-01", "20260101/..", "2026-01-01/../../x", "abc", "2026-1-1x"])
def test_safe_iso_date_rejects_non_dates(value):
    with pytest.raises(InvalidInputError):
        safe_iso_date(value, "effective_date")


def test_safe_iso_date_normalises_date_objects():
    from datetime import date

    assert safe_iso_date(date(2026, 7, 1), "effective_date") == "2026-07-01"


@pytest.mark.parametrize("value", ["../drf", "a/b", "", "a" * 81])
def test_safe_id_rejects_path_like_values(value):
    with pytest.raises(InvalidInputError):
        safe_id(value, "draft_id")


def test_target_path_rejects_a_traversing_effective_date(admin):
    yaml_content = 'effective_date: "2026-01-01/../../../../evil"\n'
    with pytest.raises(InvalidInputError):
        _target_path("tax", "kr_income", 2026, yaml_content)


def test_target_path_rejects_a_traversing_domain(admin):
    with pytest.raises(InvalidInputError):
        _target_path("../tax", "kr_income", 2026, "effective_date: 2026-01-01\n")


def test_target_path_stays_inside_the_override_dir(admin):
    from sootool.policy_mgmt.paths import get_override_policy_dir

    path = _target_path("tax", "kr_income", 2026, "effective_date: 2026-01-01\n")
    assert path.resolve().is_relative_to(get_override_policy_dir().resolve())


def test_draft_paths_reject_traversing_ids(admin):
    with pytest.raises(InvalidInputError):
        drafts.load_draft("../../etc/passwd")


def test_loader_ignores_unsafe_domain_and_key():
    assert loader._discover("../policies/tax", "kr_income", 2026) == []
    assert loader._discover("tax", "../kr_income", 2026) == []


def test_propose_rejects_unsafe_names(admin):
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("sootool.policy_propose", domain="../tax", name="kr_income", year=2026, yaml_content="x: 1")


def test_activate_refuses_a_draft_that_failed_validation(admin):
    proposed = REGISTRY.invoke(
        "sootool.policy_propose", domain="tax", name="kr_income", year=2026, yaml_content="not: valid\n",
    )
    assert proposed["validation"]["status"] == "error"
    result = REGISTRY.invoke("sootool.policy_activate", draft_id=proposed["draft_id"])
    assert result["error"] == "validation_failed"
