"""요청 단위 컨텍스트: 로케일, 무상태 여부, 인증 범위.

MCP 2026-07-28 사양은 프로토콜 세션을 없애고 모든 요청을 독립으로 다룬다. 네트워크 전송
(HTTP, SSE, Unix 소켓)의 미들웨어가 요청마다 이 값을 설정하고, 도구는 같은 요청 안에서만
읽는다. 값이 설정되지 않은 호출(stdio, 프로세스 내 직접 호출)은 로컬 신뢰 컨텍스트로 본다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import contextvars
from collections.abc import Callable, Iterator
from concurrent.futures import Executor, Future
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Final

SCOPE_READ:         Final = "read"
SCOPE_POLICY_WRITE: Final = "policy-write"

# Accept-Language 에서 해석한 로케일. None 이면 요청이 로케일을 지정하지 않았다.
REQUEST_LOCALE: ContextVar[str | None] = ContextVar("sootool_request_locale", default=None)

# True 이면 호출 이력(세션)을 쓰지 않는 요청이다. 네트워크 전송의 요청이 해당한다.
STATELESS_REQUEST: ContextVar[bool] = ContextVar("sootool_stateless_request", default=False)

# 요청의 인증 범위. None 이면 범위가 부여되지 않은 요청이다. 로컬(stdio, 프로세스 내)은 모든 범위를
# 가진 것으로 보고, 네트워크 요청은 아무 범위도 갖지 않은 것으로 본다(has_scope 참고).
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
    """현재 요청이 범위를 가졌는지 반환한다.

    범위가 부여되지 않은 요청(None)은 출처에 따라 갈린다. 로컬 호출(stdio, 프로세스 내)은 모든 범위를
    가진 것으로 보지만, 네트워크 요청(무상태 표식이 있는 요청)은 아무 범위도 갖지 않은 것으로 거부한다.
    인증을 구성하지 않았거나 미들웨어를 거치지 않은 네트워크 경로가 쓰기 권한을 얻지 못하게 하는
    기본 거부다. 신뢰하는 네트워크 계열 전송(Unix 소켓)은 미들웨어가 범위를 명시적으로 부여한다.
    """
    scopes = REQUEST_SCOPES.get()
    if scopes is None:
        return not STATELESS_REQUEST.get()
    return scope in scopes


def submit_with_context(pool: Executor, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
    """현재 컨텍스트를 복사해 워커 스레드에서 ``fn`` 을 실행한다.

    ThreadPoolExecutor 는 contextvar 를 상속하지 않으므로, batch·pipeline 의 중첩 호출이 요청의
    로케일, 무상태 표식, 인증 범위, 정책 해석 시점을 잃지 않게 호출마다 컨텍스트를 복사한다.
    """
    return pool.submit(contextvars.copy_context().run, fn, *args, **kwargs)
