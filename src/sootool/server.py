from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from sootool.boundary import SooToolServer, with_error_contract
from sootool.core.registry import REGISTRY, ToolEntry
from sootool.runtime import (
    ArithmeticResult,
    _apply_trace_level,
    _enforce_payload_limit,
    _hints_post_processor,
    _integrity_post_processor,
    _load_modules,
    _parse_request_json,
    _register_core_tools,
)

# 실행 기반은 sootool.runtime 으로 옮겼다. 기존 import 경로를 유지하기 위해 다시 내보낸다.
__all__ = [
    "ArithmeticResult",
    "_apply_trace_level",
    "_enforce_payload_limit",
    "_hints_post_processor",
    "_integrity_post_processor",
    "_load_modules",
    "_parse_request_json",
    "_register_core_tools",
    "build_server",
    "invoke_tool",
]

_SOOTOOL_INSTRUCTIONS = """\
SooTool은 LLM이 직접 계산해서는 안 되는 요청(산수, 세액, 할인율, 통계, 날짜 차이 등)을
100% 결정론적 Decimal 경로로 대체합니다.

세션 시작 시 sootool.skill_guide()를 호출해 트리거 테이블을 숙지하세요.
수치 계산이 포함된 응답에서는 사전에 해당 도메인 도구를 호출하고 trace를 사용자에게
제시하세요. 프롬프트 내 직접 산술을 금지합니다.

핵심 원칙:
- 숫자 연산은 core.add/sub/mul/div 또는 core.batch/pipeline으로 처리
- 세금·부동산은 tax.* / realestate.* (year 인자 필수)
- 금융 계산은 finance.* (Decimal 복리 정확도)
- 통계는 stats.* / probability.* (scipy/mpmath 기반)
- 복수 시나리오는 core.batch, 결과 체이닝은 core.pipeline
"""


def _bind_to_registry(entry: ToolEntry) -> Callable[..., Any]:
    """MCP 노출용 호출자를 만든다.

    REGISTRY.invoke 를 거쳐야 integrity 스탬프와 hints 후처리가 적용된다. 원본 시그니처와 반환
    타입을 유지해 입력·출력 스키마 생성이 그대로 동작하며, 입력 숫자 허용과 오류 계약
    (sootool.boundary)을 함께 적용한다.
    """
    def invoke(**kwargs: Any) -> Any:
        return REGISTRY.invoke(entry.full_name, **kwargs)

    return with_error_contract(entry.fn, invoke, signature=entry.exposed_signature())


def _annotations_for(entry: ToolEntry) -> ToolAnnotations:
    """도구 동작 특성을 MCP 어노테이션으로 변환한다.

    계산 도구는 외부 상태를 바꾸지 않는 읽기 전용이다. 정책 쓰기 도구만 readOnlyHint=False 이며
    destructiveHint 로 덮어쓰기 성격을 구분한다. 어노테이션은 클라이언트에 주는 힌트이고 접근
    통제는 admin 게이트가 담당한다.
    """
    if entry.read_only:
        return ToolAnnotations(
            read_only_hint   = True,
            idempotent_hint = entry.idempotent,
            open_world_hint = False,
        )
    return ToolAnnotations(
        read_only_hint   = False,
        destructive_hint= entry.destructive,
        idempotent_hint = entry.idempotent,
        open_world_hint = False,
    )


_LEAN_INSTRUCTIONS = """\
SooTool은 LLM이 직접 계산해서는 안 되는 요청(산수, 세액, 통계, 날짜 차이 등)을
100% 결정론적 Decimal 경로로 대체합니다. 프롬프트 내 직접 산술을 금지합니다.

도구 수가 많아 세 개의 진입 도구만 노출합니다.
1. sootool.search(query)로 도구를 찾는다.
2. sootool.describe(name)로 파라미터를 확인한다.
3. sootool.call(name, arguments)로 실행하고 trace 를 사용자에게 제시한다.
세금·부동산은 year 인자가 필수입니다. sootool.skill_guide()로 활용 가이드를 볼 수 있습니다.
"""

PROFILES = ("full", "lean")
DEFAULT_PROFILE = "full"

# 도구 목록은 프로세스 수명 동안 바뀌지 않고 모든 인증 맥락에서 같으므로 공유 캐시를 허용한다.
TOOLS_LIST_TTL_MS = 3_600_000
_CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=TOOLS_LIST_TTL_MS, scope="public"),
}


def _add_registry_tool(server: MCPServer, entry: ToolEntry) -> None:
    server.add_tool(
        _bind_to_registry(entry),
        name        = entry.full_name,
        description = entry.public_description,
        annotations = _annotations_for(entry),
    )


def build_server(profile: str = DEFAULT_PROFILE, *, expose_writes: bool = True) -> MCPServer:
    """프로파일에 따라 노출 도구를 구성한 서버를 만든다.

    full: 등록된 모든 도구를 노출한다.
    lean: 검색·설명·호출 파사드 3종과 skill_guide 만 노출해 컨텍스트 비용을 줄인다.

    expose_writes=False 이면 읽기 전용이 아닌 도구(정책 쓰기)를 노출하지 않는다. 네트워크 전송용
    서버가 쓰기 도구를 아예 광고하지 않게 하는 구성이다.
    """
    if profile not in PROFILES:
        raise ValueError(f"알 수 없는 프로파일: {profile!r} (허용: {', '.join(PROFILES)})")

    if profile == "full":
        server = SooToolServer("sootool", instructions=_SOOTOOL_INSTRUCTIONS, cache_hints=_CACHE_HINTS)
        # 결정적 순서(이름 오름차순): 클라이언트 캐시와 프롬프트 캐시 적중률을 위해 등록 순서와 무관하게 고정한다.
        for entry in sorted(REGISTRY.list(), key=lambda e: e.full_name):
            if entry.read_only or expose_writes:
                _add_registry_tool(server, entry)
        return server

    from sootool.facade import register_facade  # noqa: PLC0415

    server = SooToolServer("sootool", instructions=_LEAN_INSTRUCTIONS, cache_hints=_CACHE_HINTS)
    register_facade(server)
    for entry in REGISTRY.list():
        if entry.full_name == "sootool.skill_guide":
            _add_registry_tool(server, entry)
    return server


def invoke_tool(full_name: str, args: dict[str, Any]) -> Any:
    """Direct invocation for testing, bypasses FastMCP transport."""
    return REGISTRY.invoke(full_name, **args)
