"""HTTP+SSE legacy transport (MCP 2024-11 spec).

GET  /sse        → opens server-sent event stream (per-session)
POST /messages   → receives client messages (session_id in query string)

Activated via --enable-sse-legacy or SOOTOOL_ENABLE_SSE_LEGACY=1.
Default port: 10536.
"""
from __future__ import annotations

import logging
import os

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from sootool.middleware.auth import AuthMiddleware, BearerTokenValidator, TokenValidator
from sootool.middleware.cors import build_cors_middleware
from sootool.middleware.logging import LoggingMiddleware
from sootool.middleware.request_id import RequestIDMiddleware
from sootool.observability.health import healthz

logger = logging.getLogger("sootool.sse_legacy")


def _build_validators(auth_token: str | None) -> list[TokenValidator]:
    token = auth_token or os.environ.get("SOOTOOL_AUTH_TOKEN")
    if not token:
        return []
    return [BearerTokenValidator(token)]


def _build_cors_origins(cli_origins: list[str]) -> list[str]:
    if cli_origins:
        return cli_origins
    env_val = os.environ.get("SOOTOOL_CORS_ORIGINS", "")
    if env_val.strip():
        return [o.strip() for o in env_val.split(",") if o.strip()]
    return []


def build_sse_legacy_app(
    server: FastMCP,
    auth_token: str | None,
    cors_origins: list[str],
) -> ASGIApp:
    """Build a Starlette ASGI app serving MCP over legacy HTTP+SSE (2024-11).

    Endpoints:
        GET  /sse        — opens an SSE session stream
        POST /messages   — receives JSON-RPC from client (query: session_id)
        GET  /healthz    — health check (auth-exempt)
    """
    sse_transport = SseServerTransport("/messages/")

    mcp_server = server._mcp_server

    async def handle_sse(scope: Scope, receive: Receive, send: Send) -> None:
        async with sse_transport.connect_sse(scope, receive, send) as streams:
            await mcp_server.run(
                streams[0],
                streams[1],
                mcp_server.create_initialization_options(),
            )

    async def sse_endpoint(request: Request) -> Response:
        await handle_sse(request.scope, request.receive, request._send)
        return Response()

    routes = [
        Route("/sse", endpoint=sse_endpoint, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
        Route("/healthz", endpoint=healthz, methods=["GET"]),
    ]

    base_app: ASGIApp = Starlette(routes=routes)

    validators = _build_validators(auth_token)
    app: ASGIApp = AuthMiddleware(base_app, validators)
    app = LoggingMiddleware(app)
    app = RequestIDMiddleware(app)

    origins = _build_cors_origins(cors_origins)
    app = build_cors_middleware(app, origins)

    return app


class SseLegacyTransport:
    def __init__(
        self,
        server: FastMCP,
        host: str,
        port: int,
        auth_token: str | None,
        cors_origins: list[str],
        log_level: str = "info",
    ) -> None:
        self._server       = server
        self._host         = host
        self._port         = port
        self._auth_token   = auth_token
        self._cors_origins = cors_origins
        self._log_level    = log_level

    async def start_async(self) -> None:
        app = build_sse_legacy_app(self._server, self._auth_token, self._cors_origins)
        config = uvicorn.Config(
            app,
            host=self._host,
            port=self._port,
            log_level=self._log_level,
            loop="asyncio",
        )
        userver = uvicorn.Server(config)
        logger.info(
            "SSE legacy transport starting on %s:%d",
            self._host,
            self._port,
        )
        await userver.serve()
