"""RequestContextMiddleware 와 로케일 해석 우선순위 시험."""
from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from sootool.core.request_context import REQUEST_LOCALE, STATELESS_REQUEST, request_context
from sootool.middleware.request_context import RequestContextMiddleware
from sootool.skill_guide.locale import detect_locale


class TestDetectLocale:
    def test_arg_overrides_all(self) -> None:
        assert detect_locale(lang="en", accept_language="ko", request_locale="ko") == "en"

    def test_request_locale_overrides_accept_language_argument(self) -> None:
        assert detect_locale(accept_language="ko", request_locale="en") == "en"

    def test_request_context_is_used_when_no_explicit_value(self) -> None:
        with request_context(locale="en"):
            assert detect_locale() == "en"

    def test_explicit_request_locale_beats_context(self) -> None:
        with request_context(locale="en"):
            assert detect_locale(request_locale="ko") == "ko"

    def test_accept_language_argument_used_when_nothing_else(self) -> None:
        assert detect_locale(accept_language="en-US,en;q=0.9") == "en"

    def test_env_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "en")
        assert detect_locale() == "en"

    def test_default_ko(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOOTOOL_LOCALE", raising=False)
        assert detect_locale() == "ko"

    def test_unknown_values_fall_back(self) -> None:
        assert detect_locale(lang="fr") == "ko"
        assert detect_locale(request_locale="fr") == "ko"

    def test_priority_order_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "en")
        assert detect_locale(lang="ko", accept_language="en", request_locale="en") == "ko"
        assert detect_locale(accept_language="en", request_locale="ko") == "ko"
        assert detect_locale() == "en"


class TestDetectLocaleQValues:
    def test_q_value_ordering(self) -> None:
        assert detect_locale(accept_language="en-US;q=0.5,ko-KR;q=0.9,fr;q=0.1") == "ko"

    def test_implicit_q1_takes_priority(self) -> None:
        assert detect_locale(accept_language="ko-KR,en-US;q=0.9") == "ko"

    def test_unsupported_all_entries_falls_back(self) -> None:
        assert detect_locale(accept_language="fr,de;q=0.8") == "ko"


def _probe_client() -> TestClient:
    async def probe(request: Request) -> JSONResponse:  # noqa: ARG001
        return JSONResponse({"locale": REQUEST_LOCALE.get(), "stateless": STATELESS_REQUEST.get()})

    return TestClient(RequestContextMiddleware(Starlette(routes=[Route("/", probe)])))


class TestRequestContextMiddleware:
    def test_accept_language_becomes_request_locale(self) -> None:
        body = _probe_client().get("/", headers={"Accept-Language": "en-US,en;q=0.9,ko;q=0.5"}).json()
        assert body["locale"] == "en"

    def test_korean_header(self) -> None:
        assert _probe_client().get("/", headers={"Accept-Language": "ko-KR,ko;q=0.9"}).json()["locale"] == "ko"

    def test_no_header_leaves_locale_unset(self) -> None:
        assert _probe_client().get("/").json()["locale"] is None

    def test_unsupported_locale_defaults_to_ko(self) -> None:
        assert _probe_client().get("/", headers={"Accept-Language": "fr,de;q=0.8"}).json()["locale"] == "ko"

    def test_every_request_is_marked_stateless(self) -> None:
        assert _probe_client().get("/").json()["stateless"] is True

    def test_values_are_restored_after_the_request(self) -> None:
        _probe_client().get("/", headers={"Accept-Language": "en"})
        assert REQUEST_LOCALE.get() is None
        assert STATELESS_REQUEST.get() is False

    def test_consecutive_requests_do_not_share_locale(self) -> None:
        client = _probe_client()
        assert client.get("/", headers={"Accept-Language": "en"}).json()["locale"] == "en"
        assert client.get("/").json()["locale"] is None

    def test_non_http_scopes_pass_through(self) -> None:
        import asyncio

        seen: list[str] = []

        async def app(scope, receive, send):  # type: ignore[no-untyped-def]
            seen.append(scope["type"])

        asyncio.run(RequestContextMiddleware(app)({"type": "lifespan"}, None, None))
        assert seen == ["lifespan"]
