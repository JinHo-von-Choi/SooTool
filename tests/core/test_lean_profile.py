from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from sootool import server as S
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_LEAN_TOOLS = {"sootool.search", "sootool.describe", "sootool.call", "sootool.skill_guide"}
_LEAN_PAYLOAD_LIMIT_BYTES = 10_000


@pytest.fixture(scope="module")
def lean() -> Any:
    S._load_modules()
    return S.build_server(profile="lean")


def _call(server: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    _content, structured = asyncio.run(server.call_tool(name, args))
    return dict(structured)


def test_lean_profile_exposes_only_facade_and_skill_guide(lean):
    assert {t.name for t in asyncio.run(lean.list_tools())} == _LEAN_TOOLS


def test_lean_tool_list_stays_within_payload_budget(lean):
    tools   = asyncio.run(lean.list_tools())
    payload = json.dumps(
        [t.model_dump(mode="json", exclude_none=True) for t in tools],
        ensure_ascii=False, separators=(",", ":"),
    )
    assert len(payload.encode("utf-8")) <= _LEAN_PAYLOAD_LIMIT_BYTES


def test_lean_tools_are_read_only_annotated(lean):
    for tool in asyncio.run(lean.list_tools()):
        assert tool.annotations.readOnlyHint is True, tool.name


def test_full_profile_is_unchanged_default():
    S._load_modules()
    default = {t.name for t in asyncio.run(S.build_server().list_tools())}
    full    = {t.name for t in asyncio.run(S.build_server(profile="full").list_tools())}
    assert default == full == {e.full_name for e in REGISTRY.list()}


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError):
        S.build_server(profile="tiny")


def test_search_describe_call_flow(lean):
    hits = _call(lean, "sootool.search", {"query": "core.add"})["results"]
    assert hits[0]["name"] == "core.add"

    info = _call(lean, "sootool.describe", {"name": "core.add"})
    assert [p["name"] for p in info["parameters"]] == ["operands", "trace_level"]

    out = _call(lean, "sootool.call", {"name": "core.add", "arguments": {"operands": ["0.1", "0.2"]}})
    assert out["result"] == "0.3"
    assert len(out["_meta"]["integrity"]["input_hash"]) == 64


def test_call_result_matches_direct_invocation(lean):
    via_facade = _call(lean, "sootool.call", {"name": "core.add", "arguments": {"operands": ["1", "2"]}})
    direct     = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert via_facade["result"] == direct["result"]
    assert via_facade["_meta"]["integrity"]["input_hash"] == direct["_meta"]["integrity"]["input_hash"]


def test_call_rejects_non_read_only_tool(lean):
    with pytest.raises(Exception) as info:
        _call(lean, "sootool.call", {"name": "sootool.policy_activate", "arguments": {"draft_id": "x"}})
    assert "읽기 전용" in str(info.value)


def test_call_rejects_bad_arguments_with_typed_error():
    from sootool.facade import call

    S._load_modules()
    with pytest.raises(InvalidInputError):
        call("core.sub", {"a": "1"})


def test_call_unknown_tool_reports_candidates():
    from sootool.facade import call

    S._load_modules()
    with pytest.raises(InvalidInputError) as info:
        call("finance.loan", {})
    assert "finance.loan_schedule" in str(info.value)
