"""폐기 예고된 도구는 목록 설명, 도구 설명(describe), 응답 메타에 표기된다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import asyncio

import pytest

from sootool import server
from sootool.core.catalog import describe_tool
from sootool.core.registry import REGISTRY
from sootool.core.toolspec import tool_spec

_DEPRECATION = {"replacement": "core.add", "remove_in": "2.0.0", "since": "1.2.0"}


@pytest.fixture
def deprecated_tool():
    server._load_modules()

    @REGISTRY.tool(
        namespace="core", name="zz_deprecated_demo", description="폐기 표기 시험용 도구, 결과로 입력을 그대로 돌려준다.",
        deprecated=_DEPRECATION,
    )
    def demo(value: str) -> dict[str, object]:
        return {"result": value, "trace": {"tool": "core.zz_deprecated_demo", "formula": "value", "inputs": {}, "output": value}}

    try:
        yield REGISTRY._tools["core.zz_deprecated_demo"]
    finally:
        REGISTRY._tools.pop("core.zz_deprecated_demo", None)


def test_public_description_carries_the_notice(deprecated_tool):
    text = deprecated_tool.public_description
    assert text.startswith("[폐기 예정, 대체: core.add, 제거 예정: 2.0.0]")
    assert deprecated_tool.description in text


def test_tool_list_shows_the_notice(deprecated_tool):
    tools = {t.name: t for t in asyncio.run(server.build_server("full").list_tools())}
    assert tools["core.zz_deprecated_demo"].description.startswith("[폐기 예정")


def test_describe_and_spec_expose_the_deprecation(deprecated_tool):
    assert describe_tool(deprecated_tool)["deprecated"] == _DEPRECATION
    assert tool_spec(deprecated_tool).deprecated == _DEPRECATION


def test_response_meta_marks_the_call(deprecated_tool):
    result = REGISTRY.invoke("core.zz_deprecated_demo", value="1")
    assert result["_meta"]["deprecated"] == _DEPRECATION


def test_regular_tools_are_not_marked():
    server._load_modules()
    assert "deprecated" not in REGISTRY.invoke("core.add", operands=["1", "2"])["_meta"]
    assert REGISTRY._tools["core.add"].public_description == REGISTRY._tools["core.add"].description
