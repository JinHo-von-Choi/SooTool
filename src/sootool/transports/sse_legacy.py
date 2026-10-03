"""HTTP+SSE 레거시 전송 (MCP 2024-11).

MCP 2026-07-28 사양에서 폐기(Deprecated)된 전송이다. 기존 클라이언트 호환을 위해 SDK 의
``sse_app`` 으로 제공하며 다음 마이너 릴리스에서 제거한다. 새 연동은 Streamable HTTP 를 쓴다.

GET  /sse        server-sent event 스트림을 연다
POST /messages/  클라이언트 메시지를 받는다 (쿼리: session_id)

--enable-sse-legacy 또는 SOOTOOL_ENABLE_SSE_LEGACY=1 로 켠다. 기본 포트는 10536.
"""
from __future__ import annotations

import logging

import uvicorn
from mcp.server.mcpserver import MCPServer
from starlette.types import ASGIApp

from sootool.transports.common import compose_with_health, wrap_with_middleware

logger = logging.getLogger("sootool.sse_legacy")

DEPRECATION_MESSAGE = (
    "HTTP+SSE transport is deprecated by the MCP specification (2026-07-28) and will be "
    "removed in the next minor release. Migrate clients to Streamable HTTP."
)


def build_sse_legacy_app(
    server:       MCPServer,
    auth_token:   str | None,
    cors_origins: list[str],
    *,
    host:         str        = "127.0.0.1",
    require_auth: bool       = True,
    admin_token:  str | None = None,
) -> ASGIApp:
    """레거시 HTTP+SSE ASGI 앱을 만든다. ``/healthz`` 는 인증 없이 응답한다."""
    sse_asgi: ASGIApp = server.sse_app(host=host)
    return wrap_with_middleware(
        compose_with_health(sse_asgi),
        auth_token,
        cors_origins,
        require_auth=require_auth,
        admin_token=admin_token,
    )


class SseLegacyTransport:
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
        logger.warning(DEPRECATION_MESSAGE)
        app = build_sse_legacy_app(
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
        logger.info("SSE legacy transport starting on %s:%d", self._host, self._port)
        await uvicorn.Server(config).serve()
