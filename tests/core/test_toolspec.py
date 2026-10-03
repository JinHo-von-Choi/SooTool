"""ToolSpec 가 모든 도구에 대해 일관된 메타데이터를 낸다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import re

import pytest

from sootool import server
from sootool.core.registry import REGISTRY
from sootool.core.toolspec import EXACTNESS, HEAVY_TOOLS, NAMESPACE_TAGS, SINCE, tool_spec

_SEMVER = re.compile(r"\d+\.\d+\.\d+")


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def _specs():
    return [tool_spec(e) for e in REGISTRY.list()]


def test_every_tool_has_complete_metadata():
    for spec in _specs():
        assert spec.exactness in EXACTNESS.values(), spec.full_name
        assert _SEMVER.fullmatch(spec.since), spec.full_name
        assert _SEMVER.fullmatch(spec.version), spec.full_name
        assert spec.cost in ("light", "heavy"), spec.full_name
        assert spec.tags, spec.full_name
        assert spec.aliases, spec.full_name


def test_every_namespace_has_tags():
    assert {e.namespace for e in REGISTRY.list()} <= set(NAMESPACE_TAGS)


def test_since_and_heavy_tables_point_to_registered_tools():
    names = {e.full_name for e in REGISTRY.list()}
    assert set(SINCE) <= names
    assert HEAVY_TOOLS <= names


def test_policy_and_admin_tools_are_tagged():
    by_name = {s.full_name: s for s in _specs()}
    assert "policy" in by_name["tax.kr_income"].tags
    assert "admin" in by_name["sootool.policy_activate"].tags
    assert "admin" not in by_name["tax.kr_income"].tags
