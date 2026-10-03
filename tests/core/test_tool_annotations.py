from __future__ import annotations

import asyncio
from typing import Any

import pytest

_WRITE_TOOLS = frozenset({
    "sootool.policy_propose",
    "sootool.policy_activate",
    "sootool.policy_rollback",
    "sootool.policy_import",
})


@pytest.fixture(scope="module")
def listed() -> dict[str, Any]:
    from sootool import server as S
    S._load_modules()
    return {t.name: t for t in asyncio.run(S.build_server().list_tools())}


def test_every_tool_declares_annotations(listed):
    missing = [n for n, t in listed.items() if t.annotations is None]
    assert not missing, missing


def test_no_tool_reaches_the_open_world(listed):
    assert all(t.annotations.open_world_hint is False for t in listed.values())


def test_only_policy_write_tools_are_not_read_only(listed):
    writers = {n for n, t in listed.items() if t.annotations.read_only_hint is False}
    assert writers == _WRITE_TOOLS


def test_calculation_tools_are_read_only_and_idempotent(listed):
    for name, tool in listed.items():
        if name in _WRITE_TOOLS:
            continue
        assert tool.annotations.read_only_hint is True, name
        assert tool.annotations.idempotent_hint is True, name


def test_overwriting_write_tools_are_marked_destructive(listed):
    for name in ("sootool.policy_activate", "sootool.policy_rollback", "sootool.policy_import"):
        assert listed[name].annotations.destructive_hint is True, name
    assert listed["sootool.policy_propose"].annotations.destructive_hint is False


def test_registry_invariant_destructive_implies_not_read_only():
    from sootool import server as S
    from sootool.core.registry import REGISTRY

    S._load_modules()
    for entry in REGISTRY.list():
        if entry.destructive:
            assert not entry.read_only, entry.full_name
