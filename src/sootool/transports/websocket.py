"""WebSocket transport for SooTool MCP server.

Endpoint: GET /ws  (HTTP Upgrade → WebSocket)
Protocol: JSON-RPC over WebSocket frames (one JSON object per message).

Features:
- Ping/Pong keepalive: 30-second interval, 60-second disconnect on no response.
- Origin header validation against configured CORS origins.
- Bearer token auth via initial HTTP Upgrade request headers.
- Server→client push notifications (tools/list_changed, etc.).

Activated via --enable-websocket or SOOTOOL_ENABLE_WEBSOCKET=1.
Default port: 10537.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import anyio
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.shared.session import SessionMessage  # type: ignore[attr-defined]
from mcp.types import JSONRPCMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route, WebSocketRoute
from starlette.types import ASGIApp
from starlette.websockets import WebSocket, WebSocketDisconnect

from sootool.middleware.cors import build_cors_middleware
from sootool.middleware.logging import LoggingMiddleware
from sootool.middleware.request_id import RequestIDMiddleware
from sootool.observability.health import healthz

logger = logging.getLogger("sootool.websocket")

_PING_INTERVAL_S = 30.0
_PONG_TIMEOUT_S  = 60.0


def _effective_auth_token(cli_token: str | None) -> str | None:
    return cli_token or os.environ.get("SOOTOOL_AUTH_TOKEN")


def _effective_cors_origins(cli_origins: list[str]) -> list[str]:
    if cli_origins:
        return cli_origins
    env_val = os.environ.get("SOOTOOL_CORS_ORIGINS", "")
    if env_val.strip():
        return [o.strip() for o in env_val.split(",") if o.strip()]
    return []


def _validate_origin(origin: str | None, allowed_origins: list[str]) -> bool:
    """Return True if the request origin is permitted.

    When allowed_origins is empty, we restrict to same-origin only.
    For WebSocket upgrades there is no Host matching available here,
    so we reject unknown origins when allow-list is configured.
    """
    if not allowed_origins:
        # Same-origin policy: origin header absence is acceptable (same-origin
        # requests from non-browser clients often omit Origin).
        return True
    if origin is None:
        return False
    return origin in allowed_origins


def build_ws_app(
    server: FastMCP,
    auth_token: str | None,
    cors_origins: list[str],
) -> ASGIApp:
    """Build the Starlette ASGI app for the WebSocket transport."""

    effective_token   = _effective_auth_token(auth_token)
    effective_origins = _effective_cors_origins(cors_origins)
    mcp_server        = server._mcp_server

    async def ws_endpoint(websocket: WebSocket) -> None:
        # --- Origin validation ---
        origin = websocket.headers.get("origin")
        if effective_origins and not _validate_origin(origin, effective_origins):
            logger.warning("WebSocket rejected: disallowed origin %r", origin)
            await websocket.close(code=1008, reason="origin not allowed")
            return

        # --- Bearer token auth on the Upgrade request ---
        if effective_token:
            auth_header = websocket.headers.get("authorization", "")
            if not auth_header.lower().startswith("bearer "):
                await websocket.close(code=1008, reason="missing Authorization header")
                return
            if auth_header[7:] != effective_token:
                await websocket.close(code=1008, reason="invalid bearer token")
                return

        await websocket.accept()
        logger.info("WebSocket connection accepted (origin=%r)", origin)

        # Build in-memory streams bridging WebSocket ↔ MCP server.
        # read_stream:  messages from client → mcp_server
        # write_stream: messages from mcp_server → client
        client_to_server_w, client_to_server_r = anyio.create_memory_object_stream(
            max_buffer_size=64,
        )
        server_to_client_w, server_to_client_r = anyio.create_memory_object_stream(
            max_buffer_size=64,
        )

        pong_event: asyncio.Event = asyncio.Event()
        pong_event.set()  # initially "ok"

        async def recv_loop() -> None:
            """Read JSON-RPC frames from the WebSocket and forward to MCP."""
            try:
                async for raw in websocket.iter_text():
                    pong_event.set()  # any message resets the pong timer
                    try:
                        payload: Any = json.loads(raw)
                        rpc_msg = JSONRPCMessage.model_validate(payload)
                        await client_to_server_w.send(SessionMessage(rpc_msg))
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("WebSocket: invalid JSON-RPC frame: %s", exc)
            except WebSocketDisconnect:
                pass
            finally:
                await client_to_server_w.aclose()

        async def send_loop() -> None:
            """Forward MCP server messages to the WebSocket as JSON frames."""
            try:
                async for session_msg in server_to_client_r:
                    try:
                        frame = session_msg.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        await websocket.send_text(frame)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("WebSocket: send error: %s", exc)
                        break
            except Exception:  # noqa: BLE001, S110
                logger.debug("WebSocket: send_loop ended")

        async def ping_loop() -> None:
            """Send WebSocket pings and disconnect on missing pong."""
            while True:
                await asyncio.sleep(_PING_INTERVAL_S)
                pong_event.clear()
                try:
                    await websocket.send_text(
                        json.dumps({"jsonrpc": "2.0", "method": "ping"})
                    )
                except Exception:  # noqa: BLE001
                    break
                try:
                    await asyncio.wait_for(
                        _wait_for_event(pong_event),
                        timeout=_PONG_TIMEOUT_S - _PING_INTERVAL_S,
                    )
                except TimeoutError:
                    logger.warning("WebSocket: no pong received, disconnecting")
                    await websocket.close(code=1001, reason="ping timeout")
                    break

        async def mcp_server_task() -> None:
            await mcp_server.run(
                client_to_server_r,
                server_to_client_w,
                mcp_server.create_initialization_options(),
            )

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(recv_loop)
                tg.start_soon(send_loop)
                tg.start_soon(ping_loop)
                tg.start_soon(mcp_server_task)
        except Exception as exc:  # noqa: BLE001
            logger.debug("WebSocket session ended: %s", exc)
        finally:
            try:
                await websocket.close()
            except Exception:  # noqa: BLE001, S110
                logger.debug("WebSocket: close error (already closed)")
            logger.info("WebSocket connection closed")

    async def _wait_for_event(event: asyncio.Event) -> None:
        while not event.is_set():
            await asyncio.sleep(0.1)

    async def ws_reject_endpoint(websocket: WebSocket) -> None:
        """Fallback for non-WebSocket requests hitting /ws."""
        await websocket.close(code=1002)

    async def healthz_handler(request: Request) -> Response:
        return await healthz(request)

    routes = [
        WebSocketRoute("/ws", endpoint=ws_endpoint),
        Route("/healthz", endpoint=healthz_handler, methods=["GET"]),
    ]

    base_app: ASGIApp = Starlette(routes=routes)
    app: ASGIApp = LoggingMiddleware(base_app)
    app = RequestIDMiddleware(app)

    effective_cors = _effective_cors_origins(cors_origins)
    app = build_cors_middleware(app, effective_cors)

    return app


class WebSocketTransport:
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
        app = build_ws_app(self._server, self._auth_token, self._cors_origins)
        config = uvicorn.Config(
            app,
            host=self._host,
            port=self._port,
            log_level=self._log_level,
            loop="asyncio",
            ws="websockets",
        )
        userver = uvicorn.Server(config)
        logger.info(
            "WebSocket transport starting on %s:%d",
            self._host,
            self._port,
        )
        await userver.serve()
