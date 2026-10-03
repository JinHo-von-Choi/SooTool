"""경량 프로파일 파사드: sootool.search / sootool.describe / sootool.call.

전체 도구(264개) 정의를 매 턴 컨텍스트에 싣는 대신 세 도구만 노출하고, 필요한 도구를
검색 -> 설명 -> 호출 순서로 찾아 쓰게 한다. 호출은 REGISTRY.invoke 를 거치므로 대상 도구의
integrity 스탬프와 hints 후처리가 그대로 적용된다. 읽기 전용 도구만 호출할 수 있으며 정책
쓰기 도구는 full 프로파일에서만 사용한다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from sootool.core.catalog import (
    bind_call_arguments,
    describe_tool,
    resolve_tool,
    search_tools,
)
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def search(query: str, limit: int = 10, namespace: str | None = None) -> dict[str, Any]:
    return {"results": search_tools(REGISTRY, query, limit=limit, namespace=namespace)}


def describe(name: str) -> dict[str, Any]:
    return describe_tool(resolve_tool(REGISTRY, name))


def call(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = resolve_tool(REGISTRY, name)
    if not entry.read_only:
        raise InvalidInputError(
            f"{entry.full_name} 은(는) 읽기 전용이 아니어서 sootool.call 로 호출할 수 없습니다. "
            "full 프로파일에서 직접 호출하세요."
        )
    result: dict[str, Any] = REGISTRY.invoke(entry.full_name, **bind_call_arguments(entry, arguments))
    return result


def register_facade(server: FastMCP) -> None:
    server.add_tool(
        search,
        name        = "sootool.search",
        description = (
            "계산 도구 카탈로그를 질의어로 검색한다. 이름과 설명에서 일치하는 도구를 점수 순으로 "
            "반환한다. namespace 로 도메인(tax, finance, stats 등)을 좁힐 수 있다."
        ),
        annotations = _READ_ONLY,
    )
    server.add_tool(
        describe,
        name        = "sootool.describe",
        description = (
            "도구 하나의 전체 설명, 파라미터(이름, 타입, 필수 여부, 기본값), 반환 형식을 반환한다. "
            "sootool.call 호출 전에 파라미터를 확인할 때 사용한다."
        ),
        annotations = _READ_ONLY,
    )
    server.add_tool(
        call,
        name        = "sootool.call",
        description = (
            "name 으로 지정한 읽기 전용 계산 도구를 arguments(객체)로 실행한다. 결과, trace, "
            "_meta.integrity 는 대상 도구를 직접 호출한 결과와 같다."
        ),
        annotations = _READ_ONLY,
    )
