from __future__ import annotations

import hmac
from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from sootool.core.request_context import REQUEST_SCOPES, SCOPE_POLICY_WRITE, SCOPE_READ

_SKIP_PATHS = frozenset({"/healthz"})


class TokenValidator(Protocol):
    scopes: frozenset[str]

    def validate(self, token: str) -> bool: ...


class BearerTokenValidator:
    """상수 시간 비교로 Bearer 토큰을 검증하고, 일치하면 ``scopes`` 범위를 부여한다."""

    def __init__(self, expected: str, scopes: frozenset[str] = frozenset({SCOPE_READ})) -> None:
        self._expected = expected
        self.scopes    = scopes

    def validate(self, token: str) -> bool:
        return hmac.compare_digest(token.encode("utf-8"), self._expected.encode("utf-8"))


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication middleware.

    If no validators are configured the middleware is a pass-through and no scope
    restriction is applied. Skip paths (e.g. /healthz) always bypass auth.

    A matching validator grants its scopes for the duration of the request. Validators are
    checked in order and every validator is evaluated so the check time does not depend on
    which one matches.
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
        granted: frozenset[str] | None = None
        for validator in self._validators:
            if validator.validate(token) and granted is None:
                granted = validator.scopes
        if granted is None:
            return JSONResponse({"error": "invalid bearer token"}, status_code=401)

        scope_token = REQUEST_SCOPES.set(granted)
        try:
            return await _call_next(request)
        finally:
            REQUEST_SCOPES.reset(scope_token)


class LocalTrustMiddleware:
    """접근 통제를 전송 바깥(소켓 파일 권한)에 맡기는 로컬 전송용 미들웨어.

    네트워크 계열 요청은 범위가 없으면 읽기·쓰기 모두 거부되므로, 파일 권한으로 보호되는 Unix 소켓
    요청에는 모든 범위를 명시적으로 부여한다.
    """

    _SCOPES = frozenset({SCOPE_READ, SCOPE_POLICY_WRITE})

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        token = REQUEST_SCOPES.set(self._SCOPES)
        try:
            await self._app(scope, receive, send)
        finally:
            REQUEST_SCOPES.reset(token)
