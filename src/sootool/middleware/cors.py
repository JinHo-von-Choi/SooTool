from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware as StarletteCorsMW
from starlette.types import ASGIApp


def build_cors_middleware(app: ASGIApp, allowed_origins: list[str]) -> ASGIApp:
    """Wrap app with CORSMiddleware.

    If allowed_origins is empty, only same-origin requests are allowed
    (no CORS headers emitted, browsers enforce same-origin by default).
    When origins are configured, also allow the MCP-required headers and methods.
    """
    if not allowed_origins:
        return app

    return StarletteCorsMW(
        app,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "authorization", "x-request-id", "mcp-session-id"],
        expose_headers=["x-request-id"],
    )
