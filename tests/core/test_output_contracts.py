"""도구 결과 스키마 계약 시험.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import asyncio

import pytest

from sootool import server
from sootool.core.registry import REGISTRY
from sootool.core.result_types import declared_result_type

# 정밀 결과 타입으로 전환이 끝나지 않은 네임스페이스. 전환하면 이 목록에서 뺀다.
_PENDING_NAMESPACES: frozenset[str] = frozenset()


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def test_converted_namespaces_declare_precise_result_types():
    untyped = [
        e.full_name for e in REGISTRY.list()
        if e.namespace not in _PENDING_NAMESPACES and declared_result_type(e.fn) is None
    ]
    assert not untyped, untyped


def test_pending_list_is_honest():
    """전환이 끝난 네임스페이스가 목록에 남아 있지 않다."""
    finished = [
        ns for ns in sorted(_PENDING_NAMESPACES)
        if all(declared_result_type(e.fn) is not None for e in REGISTRY.list() if e.namespace == ns)
    ]
    assert not finished, f"전환이 끝났으니 _PENDING_NAMESPACES 에서 빼세요: {finished}"


def test_typed_tools_publish_a_specific_output_schema():
    typed = [e for e in REGISTRY.list() if declared_result_type(e.fn) is not None]
    if not typed:
        pytest.skip("정밀 타입을 선언한 도구가 아직 없음")
    mcp = server.build_server()
    schemas = {t.name: t.output_schema for t in asyncio.run(mcp.list_tools())}
    generic = [
        e.full_name for e in typed
        if not (schemas.get(e.full_name) or {}).get("properties")
    ]
    assert not generic, generic


_FULL_LIST_BYTES_LIMIT = 600_000


def test_full_profile_tool_list_stays_small_enough_for_streaming_clients():
    """tools/list 응답이 SSE 클라이언트의 이벤트 크기 한도(1 MiB)에 한참 못 미친다."""
    import json

    mcp   = server.build_server("full")
    tools = asyncio.run(mcp.list_tools())
    size  = sum(len(json.dumps(t.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False)) for t in tools)
    assert size < _FULL_LIST_BYTES_LIMIT, size


def test_compacted_schemas_keep_tool_specific_fields():
    mcp     = server.build_server("full")
    schemas = {t.name: t.output_schema for t in asyncio.run(mcp.list_tools())}
    props   = schemas["tax.kr_income"]["properties"]
    assert {"tax", "effective_rate", "marginal_rate", "breakdown"} <= set(props)
    assert props["_meta"] == {"type": "object", "description": props["_meta"]["description"]}
