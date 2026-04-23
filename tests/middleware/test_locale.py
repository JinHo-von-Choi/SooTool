"""Tests for LocaleMiddleware and detect_locale() priority chain."""
from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from sootool.middleware.locale import LocaleMiddleware
from sootool.skill_guide.locale import detect_locale
from sootool.skill_guide.session_state import InMemoryStore

# ---------------------------------------------------------------------------
# detect_locale() unit tests
# ---------------------------------------------------------------------------

class TestDetectLocale:
    def test_arg_overrides_all(self) -> None:
        assert detect_locale(lang="en", accept_language="ko", session_locale="ko") == "en"

    def test_session_locale_overrides_accept_language(self) -> None:
        assert detect_locale(accept_language="ko", session_locale="en") == "en"

    def test_accept_language_used_when_no_arg_or_session(self) -> None:
        assert detect_locale(accept_language="en-US,en;q=0.9") == "en"

    def test_env_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "en")
        assert detect_locale() == "en"

    def test_default_ko(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOOTOOL_LOCALE", raising=False)
        assert detect_locale() == "ko"

    def test_unknown_lang_arg_falls_back_to_ko(self) -> None:
        assert detect_locale(lang="fr") == "ko"

    def test_unknown_session_locale_skipped(self) -> None:
        result = detect_locale(session_locale="fr")
        assert result == "ko"

    def test_priority_order_full(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "en")
        # arg beats everything
        assert detect_locale(lang="ko", accept_language="en", session_locale="en") == "ko"
        # session beats accept-language
        assert detect_locale(accept_language="en", session_locale="ko") == "ko"
        # env is last resort before default
        assert detect_locale() == "en"


class TestDetectLocaleQValues:
    def test_q_value_ordering(self) -> None:
        header = "en-US;q=0.5,ko-KR;q=0.9,fr;q=0.1"
        assert detect_locale(accept_language=header) == "ko"

    def test_implicit_q1_takes_priority(self) -> None:
        header = "ko-KR,en-US;q=0.9"
        assert detect_locale(accept_language=header) == "ko"

    def test_unsupported_all_entries_falls_back(self) -> None:
        header = "fr,de;q=0.8"
        result = detect_locale(accept_language=header)
        assert result == "ko"


# ---------------------------------------------------------------------------
# InMemoryStore locale methods
# ---------------------------------------------------------------------------

class TestInMemoryStoreLocale:
    def test_set_and_get_locale(self) -> None:
        store = InMemoryStore()
        store.set_locale("session-1", "en")
        assert store.get_locale("session-1") == "en"

    def test_get_locale_unknown_session_returns_none(self) -> None:
        store = InMemoryStore()
        assert store.get_locale("nonexistent") is None

    def test_overwrite_locale(self) -> None:
        store = InMemoryStore()
        store.set_locale("s", "ko")
        store.set_locale("s", "en")
        assert store.get_locale("s") == "en"

    def test_locale_isolated_per_session(self) -> None:
        store = InMemoryStore()
        store.set_locale("s1", "ko")
        store.set_locale("s2", "en")
        assert store.get_locale("s1") == "ko"
        assert store.get_locale("s2") == "en"


# ---------------------------------------------------------------------------
# LocaleMiddleware ASGI integration tests (Starlette TestClient)
# ---------------------------------------------------------------------------

def _ok(request: Request) -> PlainTextResponse:  # noqa: ARG001
    return PlainTextResponse("ok")


def _make_client(store: InMemoryStore | None = None, session_id: str = "test") -> TestClient:
    """Build a minimal Starlette app wrapped by LocaleMiddleware."""
    app = Starlette(routes=[Route("/", _ok)])
    middleware = LocaleMiddleware(app)
    # Inject a custom STORE via monkeypatching at call site if needed.
    # For simplicity use the module-level STORE and env var for session_id.
    return TestClient(middleware, raise_server_exceptions=True)


class TestLocaleMiddleware:
    def test_accept_language_stored_in_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from sootool.skill_guide.session_state import STORE

        sid = "mw-test-ko-sync"
        monkeypatch.setenv("SOOTOOL_SESSION_ID", sid)
        client = _make_client()
        client.get("/", headers={"Accept-Language": "ko-KR,ko;q=0.9"})
        assert STORE.get_locale(sid) == "ko"

    def test_english_header_stores_en(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from sootool.skill_guide.session_state import STORE

        sid = "mw-test-en-sync"
        monkeypatch.setenv("SOOTOOL_SESSION_ID", sid)
        client = _make_client()
        client.get("/", headers={"Accept-Language": "en-US,en;q=0.9,ko;q=0.5"})
        assert STORE.get_locale(sid) == "en"

    def test_no_header_leaves_locale_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from sootool.skill_guide.session_state import STORE

        sid = "mw-test-none-sync"
        monkeypatch.setenv("SOOTOOL_SESSION_ID", sid)
        client = _make_client()
        client.get("/")
        assert STORE.get_locale(sid) is None

    def test_app_still_called(self) -> None:
        """Middleware must always delegate to the wrapped app and return 200."""
        client = _make_client()
        response = client.get("/")
        assert response.status_code == 200

    def test_unsupported_locale_defaults_ko(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from sootool.skill_guide.session_state import STORE

        sid = "mw-test-fr-sync"
        monkeypatch.setenv("SOOTOOL_SESSION_ID", sid)
        client = _make_client()
        client.get("/", headers={"Accept-Language": "fr,de;q=0.8"})
        assert STORE.get_locale(sid) == "ko"
