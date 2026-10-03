"""네트워크 전송이 공유하는 ASGI 구성 요소: 인증, CORS, 요청 컨텍스트, 로깅, /healthz."""
from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from sootool.core.request_context import SCOPE_POLICY_WRITE, SCOPE_READ
from sootool.middleware.auth import (
    AuthMiddleware,
    BearerTokenValidator,
    LocalTrustMiddleware,
    TokenValidator,
)
from sootool.middleware.cors import build_cors_middleware
from sootool.middleware.logging import LoggingMiddleware
from sootool.middleware.request_context import RequestContextMiddleware
from sootool.middleware.request_id import RequestIDMiddleware
from sootool.observability.health import healthz

AUTH_ENV_VAR  = "SOOTOOL_AUTH_TOKEN"
ADMIN_ENV_VAR = "SOOTOOL_ADMIN_TOKEN"


def build_validators(auth_token: str | None, admin_token: str | None = None) -> list[TokenValidator]:
    """읽기 토큰과 관리자 토큰으로 검증기를 만든다.

    읽기 토큰은 ``read`` 범위를, 관리자 토큰은 ``read`` 와 ``policy-write`` 범위를 부여한다.
    둘 다 없으면 인증을 하지 않는다.
    """
    read_token  = auth_token or os.environ.get(AUTH_ENV_VAR)
    write_token = admin_token or os.environ.get(ADMIN_ENV_VAR)
    validators: list[TokenValidator] = []
    if read_token:
        validators.append(BearerTokenValidator(read_token, frozenset({SCOPE_READ})))
    if write_token:
        validators.append(
            BearerTokenValidator(write_token, frozenset({SCOPE_READ, SCOPE_POLICY_WRITE}))
        )
    return validators


def build_cors_origins(cli_origins: list[str]) -> list[str]:
    if cli_origins:
        return cli_origins
    env_val = os.environ.get("SOOTOOL_CORS_ORIGINS", "")
    if env_val.strip():
        return [o.strip() for o in env_val.split(",") if o.strip()]
    return []


def compose_with_health(mcp_app: ASGIApp) -> ASGIApp:
    """``/healthz`` 는 헬스 체크로, 나머지는 MCP 앱으로 보낸다."""
    health_app: ASGIApp = Starlette(routes=[Route("/healthz", endpoint=healthz, methods=["GET"])])

    class _ComposedApp:
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope.get("path", "") == "/healthz":
                await health_app(scope, receive, send)
            else:
                await mcp_app(scope, receive, send)

    return _ComposedApp()


def wrap_with_middleware(
    app:          ASGIApp,
    auth_token:   str | None,
    cors_origins: list[str],
    *,
    require_auth: bool       = True,
    admin_token:  str | None = None,
) -> ASGIApp:
    """미들웨어 순서(안쪽부터): 인증(또는 로컬 신뢰), 요청 컨텍스트, 로깅, 요청 id, CORS.

    ``require_auth=False`` 는 파일 권한으로 접근을 통제하는 로컬 전송(Unix 소켓)용이며 모든 범위를
    명시적으로 부여한다. 인증을 켰지만 검증기가 없으면(토큰 미설정) 범위가 부여되지 않아 네트워크 요청은
    쓰기 권한을 얻지 못한다.
    """
    if require_auth:
        app = AuthMiddleware(app, build_validators(auth_token, admin_token))
    else:
        app = LocalTrustMiddleware(app)
    app = RequestContextMiddleware(app)
    app = LoggingMiddleware(app)
    app = RequestIDMiddleware(app)
    return build_cors_middleware(app, build_cors_origins(cors_origins))
