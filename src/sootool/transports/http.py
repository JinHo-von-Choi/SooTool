from __future__ import annotations

import logging

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp

from sootool.transports.common import compose_with_health, wrap_with_middleware

logger = logging.getLogger("sootool.http")


def build_http_app(
    server:       MCPServer,
    auth_token:   str | None,
    cors_origins: list[str],
    *,
    host:         str        = "127.0.0.1",
    require_auth: bool       = True,
    admin_token:  str | None = None,
    transport_security: TransportSecuritySettings | None = None,
) -> ASGIApp:
    """Streamable HTTP ASGI 앱을 만든다.

    MCP 2026-07-28 에 맞춰 무상태로 서비스한다. 모든 요청이 독립이라 라운드 로빈 로드 밸런서
    뒤에서 동작한다. ``host`` 는 SDK 의 DNS 리바인딩 보호 범위를 정한다(루프백 바인드에서만
    Host 헤더를 제한한다).
    """
    mcp_asgi: ASGIApp = server.streamable_http_app(
        stateless_http=True, host=host, transport_security=transport_security,
    )
    return wrap_with_middleware(
        compose_with_health(mcp_asgi),
        auth_token,
        cors_origins,
        require_auth=require_auth,
        admin_token=admin_token,
    )


class HttpTransport:
    def __init__(
        self,
        server:       MCPServer,
        host:         str,
        port:         int,
        auth_token:   str | None,
        cors_origins: list[str],
        log_level:    str        = "info",
        admin_token:  str | None = None,
    ) -> None:
        self._server       = server
        self._host         = host
        self._port         = port
        self._auth_token   = auth_token
        self._admin_token  = admin_token
        self._cors_origins = cors_origins
        self._log_level    = log_level

    async def start_async(self) -> None:
        app = build_http_app(
            self._server,
            self._auth_token,
            self._cors_origins,
            host=self._host,
            admin_token=self._admin_token,
        )
        config = uvicorn.Config(
            app,
            host=self._host,
            port=self._port,
            log_level=self._log_level,
            loop="asyncio",
        )
        await uvicorn.Server(config).serve()
