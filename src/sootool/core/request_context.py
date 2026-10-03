"""요청 단위 컨텍스트: 로케일, 무상태 여부, 인증 범위.

MCP 2026-07-28 사양은 프로토콜 세션을 없애고 모든 요청을 독립으로 다룬다. 네트워크 전송
(HTTP, SSE, Unix 소켓)의 미들웨어가 요청마다 이 값을 설정하고, 도구는 같은 요청 안에서만
읽는다. 값이 설정되지 않은 호출(stdio, 프로세스 내 직접 호출)은 로컬 신뢰 컨텍스트로 본다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Final

SCOPE_READ:         Final = "read"
SCOPE_POLICY_WRITE: Final = "policy-write"

# Accept-Language 에서 해석한 로케일. None 이면 요청이 로케일을 지정하지 않았다.
REQUEST_LOCALE: ContextVar[str | None] = ContextVar("sootool_request_locale", default=None)

# True 이면 호출 이력(세션)을 쓰지 않는 요청이다. 네트워크 전송의 요청이 해당한다.
STATELESS_REQUEST: ContextVar[bool] = ContextVar("sootool_stateless_request", default=False)

# 요청의 인증 범위. None 이면 로컬 신뢰 컨텍스트(범위 검사 없음)다.
REQUEST_SCOPES: ContextVar[frozenset[str] | None] = ContextVar("sootool_request_scopes", default=None)


@contextmanager
def request_context(
    *,
    locale:    str | None            = None,
    stateless: bool                  = False,
    scopes:    frozenset[str] | None = None,
) -> Iterator[None]:
    """요청 범위의 컨텍스트 값을 설정하고 종료 시 복원한다."""
    tokens = (
        REQUEST_LOCALE.set(locale),
        STATELESS_REQUEST.set(stateless),
        REQUEST_SCOPES.set(scopes),
    )
    try:
        yield
    finally:
        REQUEST_SCOPES.reset(tokens[2])
        STATELESS_REQUEST.reset(tokens[1])
        REQUEST_LOCALE.reset(tokens[0])


def has_scope(scope: str) -> bool:
    """현재 요청이 범위를 가졌는지 반환한다. 로컬 신뢰 컨텍스트(None)는 모든 범위를 가진다."""
    scopes = REQUEST_SCOPES.get()
    return scopes is None or scope in scopes
