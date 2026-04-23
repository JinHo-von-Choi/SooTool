"""LocaleMiddleware — parse Accept-Language header and persist locale to SessionStore."""
from __future__ import annotations

import os

from starlette.types import ASGIApp, Receive, Scope, Send

from sootool.skill_guide.locale import SUPPORTED_LOCALES, _parse_accept_language
from sootool.skill_guide.session_state import STORE


class LocaleMiddleware:
    """Starlette middleware that reads Accept-Language from every HTTP request
    and stores the resolved locale in the InMemoryStore session entry.

    Insertion order in build_http_app: AuthMiddleware > LocaleMiddleware > CORSMiddleware.

    The session_id is read from the SOOTOOL_SESSION_ID ASGI state key that
    AuthMiddleware (or RequestIDMiddleware) is expected to populate.  When the
    key is absent the middleware falls back to the process-level stdio constant
    so it is always safe to call even outside HTTP contexts.
    """

    _STDIO_FALLBACK = "stdio-default"

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            session_id = self._resolve_session_id(scope)
            accept_language = self._extract_accept_language(scope)
            if accept_language:
                locale = self._resolve_locale(accept_language)
                STORE.set_locale(session_id, locale)
        await self._app(scope, receive, send)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_session_id(self, scope: Scope) -> str:
        state = scope.get("state") or {}
        sid = getattr(state, "session_id", None) or os.environ.get(
            "SOOTOOL_SESSION_ID", self._STDIO_FALLBACK
        )
        return str(sid)

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
