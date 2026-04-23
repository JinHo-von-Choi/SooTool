"""Tests for locale detection utility."""
from __future__ import annotations

import pytest

from sootool.skill_guide.locale import detect_locale


class TestDetectLocale:
    def test_explicit_lang_ko(self) -> None:
        assert detect_locale(lang="ko") == "ko"

    def test_explicit_lang_en(self) -> None:
        assert detect_locale(lang="en") == "en"

    def test_explicit_lang_bcp47(self) -> None:
        assert detect_locale(lang="en-US") == "en"
        assert detect_locale(lang="ko-KR") == "ko"

    def test_explicit_lang_unsupported_falls_back(self) -> None:
        assert detect_locale(lang="fr") == "ko"

    def test_accept_language_ko(self) -> None:
        assert detect_locale(accept_language="ko-KR,ko;q=0.9,en-US;q=0.8") == "ko"

    def test_accept_language_en(self) -> None:
        assert detect_locale(accept_language="en-US,en;q=0.9") == "en"

    def test_accept_language_unsupported_falls_back(self) -> None:
        result = detect_locale(accept_language="fr-FR,fr;q=0.9")
        assert result == "ko"

    def test_env_var_ko(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "ko")
        assert detect_locale() == "ko"

    def test_env_var_en(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "en")
        assert detect_locale() == "en"

    def test_env_var_unsupported_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "ja")
        assert detect_locale() == "ko"

    def test_default_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOOTOOL_LOCALE", raising=False)
        assert detect_locale() == "ko"

    def test_arg_takes_priority_over_accept_language(self) -> None:
        assert detect_locale(lang="en", accept_language="ko-KR") == "en"

    def test_arg_takes_priority_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "ko")
        assert detect_locale(lang="en") == "en"

    def test_accept_language_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOOTOOL_LOCALE", "ko")
        assert detect_locale(accept_language="en-US") == "en"
