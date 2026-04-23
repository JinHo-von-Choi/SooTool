"""sootool.skill_guide MCP tool registration."""
from __future__ import annotations

from typing import Any

from sootool.core.registry import REGISTRY
from sootool.skill_guide.anti_patterns import get_anti_patterns
from sootool.skill_guide.examples import get_examples
from sootool.skill_guide.locale import detect_locale
from sootool.skill_guide.playbooks import get_playbooks
from sootool.skill_guide.triggers import get_triggers

GUIDE_VERSION = "1.0.0"

_VALID_SECTIONS = {"triggers", "examples", "anti_patterns", "playbooks", "all"}


@REGISTRY.tool(
    namespace="sootool",
    name="skill_guide",
    description=(
        "에이전트 능동 활용 가이드 반환. "
        "section: triggers|examples|anti_patterns|playbooks|all. "
        "lang: ko(기본)|en."
    ),
    version="1.0.0",
)
def skill_guide(
    section: str = "all",
    lang: str | None = None,
) -> dict[str, Any]:
    """Return structured JSON guide for agentic tool usage.

    Args:
        section: Which section(s) to return. One of:
            triggers, examples, anti_patterns, playbooks, all.
        lang: Locale override. Detected automatically if None.
            Priority: arg > Accept-Language header > SOOTOOL_LOCALE env > ko.

    Returns:
        Structured dict with version, locale, and requested section data.
    """
    if section not in _VALID_SECTIONS:
        raise ValueError(
            f"Invalid section '{section}'. Valid values: {sorted(_VALID_SECTIONS)}"
        )

    locale = detect_locale(lang=lang)

    response: dict[str, Any] = {
        "version": GUIDE_VERSION,
        "locale":  locale,
    }

    if section in ("triggers", "all"):
        response["triggers"] = get_triggers(locale)

    if section in ("examples", "all"):
        response["examples"] = get_examples(locale)

    if section in ("anti_patterns", "all"):
        response["anti_patterns"] = get_anti_patterns(locale)

    if section in ("playbooks", "all"):
        response["playbooks"] = get_playbooks(locale)

    return response
