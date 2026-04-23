from __future__ import annotations

from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

_SKIP_PATHS = frozenset({"/healthz"})


class TokenValidator(Protocol):
    def validate(self, token: str) -> bool: ...


class BearerTokenValidator:
    def __init__(self, expected: str) -> None:
        self._expected = expected

    def validate(self, token: str) -> bool:
        return token == self._expected


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication middleware.

    If no validators are configured the middleware is a pass-through.
    Skip paths (e.g. /healthz) always bypass auth.
    """

    def __init__(self, app: ASGIApp, validators: list[TokenValidator]) -> None:
        super().__init__(app)
        self._validators = validators

    async def dispatch(self, request: Request, call_next: object) -> Response:
        from starlette.middleware.base import RequestResponseEndpoint

        _call_next: RequestResponseEndpoint = call_next  # type: ignore[assignment]

        if not self._validators or request.url.path in _SKIP_PATHS:
            return await _call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                {"error": "missing or malformed Authorization header"},
                status_code=401,
            )

        token = auth_header[7:]
        if not any(v.validate(token) for v in self._validators):
            return JSONResponse({"error": "invalid bearer token"}, status_code=401)

        return await _call_next(request)
