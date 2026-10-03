from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import pytest


def _call(server: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """FastMCP 서버에 도구 호출을 보내고 structured 결과 dict 를 반환한다."""
    result = asyncio.run(server.call_tool(name, args))
    return dict(result.structured_content)


@pytest.fixture(scope="module")
def server() -> Any:
    from sootool import server as S
    S._load_modules()
    return S.build_server()


def test_mcp_call_applies_integrity_stamp(server):
    out = _call(server, "core.add", {"operands": ["0.1", "0.2"]})
    assert out["result"] == "0.3"
    integrity = out["_meta"]["integrity"]
    assert integrity["tool_version"]
    assert len(integrity["input_hash"]) == 64


def test_mcp_call_applies_hints_post_processor(server):
    out = _call(server, "core.mul", {"operands": ["2", "3"]})
    assert "hints" in out["_meta"]
    assert out["_meta"]["session_stats"]["tool_calls"] >= 1


def test_mcp_call_preserves_result_and_trace(server):
    out = _call(server, "core.sub", {"a": "5", "b": "3"})
    assert out["result"] == "2"
    assert out["trace"]["tool"] == "core.sub"


def test_mcp_call_returns_limit_error_with_contract(server):
    result = asyncio.run(server.call_tool("probability.factorial", {"n": 10**6}))
    assert result.is_error is True
    error = result.structured_content["error"]
    assert error["code"] == "input_limit"
    assert "한도" in error["message"]


def test_input_hash_is_identical_across_mcp_and_direct_calls(server):
    from sootool.core.registry import REGISTRY

    via_mcp = _call(server, "core.add", {"operands": ["1", "2"]})
    direct  = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert via_mcp["_meta"]["integrity"]["input_hash"] == direct["_meta"]["integrity"]["input_hash"]


def test_input_hash_ignores_explicit_default_arguments():
    from sootool.core.registry import REGISTRY

    omitted  = REGISTRY.invoke("core.add", operands=["1", "2"])
    explicit = REGISTRY.invoke("core.add", operands=["1", "2"], trace_level="summary")
    assert omitted["_meta"]["integrity"]["input_hash"] == explicit["_meta"]["integrity"]["input_hash"]


def test_input_hash_differs_when_non_default_argument_changes():
    from sootool.core.registry import REGISTRY

    base = REGISTRY.invoke("core.add", operands=["1", "2"])
    full = REGISTRY.invoke("core.add", operands=["1", "2"], trace_level="full")
    assert base["_meta"]["integrity"]["input_hash"] != full["_meta"]["integrity"]["input_hash"]


def test_registered_tool_schema_matches_original_signature(server):
    from sootool.core.registry import REGISTRY

    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    for entry in REGISTRY.list():
        expected = set(inspect.signature(entry.fn).parameters)
        actual   = set(tools[entry.full_name].input_schema.get("properties", {}))
        assert actual == expected, entry.full_name


def test_every_registered_tool_is_listed(server):
    from sootool.core.registry import REGISTRY

    listed = {t.name for t in asyncio.run(server.list_tools())}
    assert {e.full_name for e in REGISTRY.list()} == listed


def test_payload_is_json_serializable(server):
    out = _call(server, "core.add", {"operands": ["1", "2"]})
    json.dumps(out)


# --- 목록 캐시 힌트와 결정적 순서 (MCP 2026-07-28) ---

def test_tools_list_declares_ttl_and_public_scope(server):
    from mcp.client import Client

    async def fetch():
        async with Client(server) as client:
            return await client.list_tools()

    result = asyncio.run(fetch())
    assert result.ttl_ms == 3_600_000
    assert result.cache_scope == "public"


def test_tools_are_listed_in_name_order(server):
    names = [t.name for t in asyncio.run(server.list_tools())]
    assert names == sorted(names)


def test_tool_listing_is_identical_across_server_instances():
    from sootool import server as S

    first  = [t.name for t in asyncio.run(S.build_server().list_tools())]
    second = [t.name for t in asyncio.run(S.build_server().list_tools())]
    assert first == second
