from __future__ import annotations

import logging
import os

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from sootool.middleware.auth import AuthMiddleware, BearerTokenValidator, TokenValidator
from sootool.middleware.cors import build_cors_middleware
from sootool.middleware.locale import LocaleMiddleware
from sootool.middleware.logging import LoggingMiddleware
from sootool.middleware.request_id import RequestIDMiddleware
from sootool.observability.health import healthz

logger = logging.getLogger("sootool.http")


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

def build_http_app(
    server: FastMCP,
    auth_token: str | None,
    cors_origins: list[str],
) -> ASGIApp:
    mcp_asgi: ASGIApp = server.streamable_http_app()

    health_route = Route("/healthz", endpoint=healthz, methods=["GET"])
    health_app: ASGIApp = Starlette(routes=[health_route])

    class _ComposedApp:
        """Route /healthz to health_app, everything else to mcp_asgi."""

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            path: str = scope.get("path", "")
            if path == "/healthz":
                await health_app(scope, receive, send)
            else:
                await mcp_asgi(scope, receive, send)

    app: ASGIApp = _ComposedApp()

    validators = _build_validators(auth_token)
    app = AuthMiddleware(app, validators)
    app = LocaleMiddleware(app)
    app = LoggingMiddleware(app)
    app = RequestIDMiddleware(app)

    origins = _build_cors_origins(cors_origins)
    app = build_cors_middleware(app, origins)

    return app


class HttpTransport:
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
        app = build_http_app(self._server, self._auth_token, self._cors_origins)
        config = uvicorn.Config(
            app,
            host=self._host,
            port=self._port,
            log_level=self._log_level,
            loop="asyncio",
        )
        userver = uvicorn.Server(config)
        await userver.serve()
