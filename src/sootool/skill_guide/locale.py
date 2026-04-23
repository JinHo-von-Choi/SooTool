"""Locale detection utility for skill_guide responses."""
from __future__ import annotations

import os

SUPPORTED_LOCALES = {"ko", "en"}
_DEFAULT_LOCALE = "ko"


def detect_locale(lang: str | None = None, accept_language: str | None = None) -> str:
    """Resolve locale with priority: arg > Accept-Language > SOOTOOL_LOCALE > ko.

    Only ko and en are supported; unknown locales fall back to ko.
    """
    if lang is not None:
        normalized = _normalize(lang)
        return normalized if normalized in SUPPORTED_LOCALES else _DEFAULT_LOCALE

    if accept_language:
        candidate = _parse_accept_language(accept_language)
        if candidate in SUPPORTED_LOCALES:
            return candidate

    env_locale = os.environ.get("SOOTOOL_LOCALE", "")
    if env_locale:
        normalized = _normalize(env_locale)
        if normalized in SUPPORTED_LOCALES:
            return normalized

    return _DEFAULT_LOCALE


def _normalize(tag: str) -> str:
    """Normalize BCP-47 tag to primary subtag: 'en-US' -> 'en', 'ko-KR' -> 'ko'."""
    return tag.strip().split("-")[0].lower()


def _parse_accept_language(header: str) -> str:
    """Extract highest-priority language from Accept-Language header.

    e.g. 'ko-KR,ko;q=0.9,en-US;q=0.8' -> 'ko'
    """
    entries: list[tuple[float, str]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        if ";q=" in part:
            lang_tag, q_str = part.split(";q=", 1)
            try:
                q = float(q_str)
            except ValueError:
                q = 0.0
        else:
            lang_tag = part
            q = 1.0
        entries.append((q, _normalize(lang_tag.strip())))

    entries.sort(key=lambda x: x[0], reverse=True)
    return entries[0][1] if entries else _DEFAULT_LOCALE
