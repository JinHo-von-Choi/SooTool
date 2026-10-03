"""RequestContextMiddleware: 요청 단위 컨텍스트(로케일, 무상태 표식)를 설정한다.

MCP 2026-07-28 사양에서 네트워크 전송의 모든 요청은 독립이다. 이 미들웨어는 요청마다
Accept-Language 에서 로케일을 해석해 요청 컨텍스트에 두고, 호출 이력을 쓰지 않는 무상태
요청임을 표시한다. 값은 요청이 끝나면 복원되므로 요청 사이에 새지 않는다.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from sootool.core.request_context import request_context
from sootool.skill_guide.locale import SUPPORTED_LOCALES, _parse_accept_language


class RequestContextMiddleware:
    """Accept-Language 를 로케일로 해석해 요청 컨텍스트에 싣는 순수 ASGI 미들웨어."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        accept_language = self._extract_accept_language(scope)
        locale = self._resolve_locale(accept_language) if accept_language else None
        with request_context(locale=locale, stateless=True):
            await self._app(scope, receive, send)

    @staticmethod
    def _extract_accept_language(scope: Scope) -> str:
        """Return the raw Accept-Language header value, or empty string."""
        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        for name, value in headers:
            if name.lower() == b"accept-language":
                return value.decode("latin-1", errors="replace")
        return ""

    @staticmethod
    def _resolve_locale(accept_language: str) -> str:
        """Map Accept-Language header to a supported locale tag."""
        candidate = _parse_accept_language(accept_language)
        return candidate if candidate in SUPPORTED_LOCALES else "ko"
