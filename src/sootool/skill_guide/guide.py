"""sootool.skill_guide MCP tool registration."""
from __future__ import annotations

from typing import Any, NotRequired, TypedDict, cast

from sootool.core.registry import REGISTRY
from sootool.core.result_types import ToolResult
from sootool.skill_guide.anti_patterns import get_anti_patterns
from sootool.skill_guide.examples import get_examples
from sootool.skill_guide.locale import detect_locale
from sootool.skill_guide.playbooks import get_playbooks
from sootool.skill_guide.triggers import get_triggers

GUIDE_VERSION = "1.0.0"

_VALID_SECTIONS = {"triggers", "examples", "anti_patterns", "playbooks", "all"}


class GuideTrigger(TypedDict):
    signal: str
    tool:   str
    reason: str


class GuideToolCall(TypedDict):
    tool: str
    args: dict[str, Any]


class GuideExample(TypedDict):
    request:         str
    tool_call:       GuideToolCall
    expected_output: dict[str, Any]


class GuideAntiPattern(TypedDict):
    pattern: str
    why:     str
    instead: str


class GuidePlaybookStep(TypedDict):
    id:   str
    tool: str
    args: dict[str, Any]


class GuidePlaybook(TypedDict):
    id:              str
    scenario:        str
    steps:           list[GuidePlaybookStep]
    expected_output: dict[str, Any]
    caveats:         list[str]
    title:           NotRequired[str]
    description:     NotRequired[str]


class SkillGuideResult(ToolResult):
    version:       str
    locale:        str
    triggers:      NotRequired[list[GuideTrigger]]
    examples:      NotRequired[list[GuideExample]]
    anti_patterns: NotRequired[list[GuideAntiPattern]]
    playbooks:     NotRequired[list[GuidePlaybook]]


@REGISTRY.tool(
    namespace="sootool",
    name="skill_guide",
    description=(
        "에이전트용 능동 활용 가이드를 반환한다. section 은 triggers(호출 신호표), examples, anti_patterns, playbooks, "
        "all(기본) 중 하나이고 lang 은 ko 또는 en 이다. lang 을 생략하면 요청 언어와 SOOTOOL_LOCALE 환경변수를 거쳐 "
        "ko 로 정해진다. 세션을 시작할 때 한 번 읽는다."
    ),
    version="1.0.0",
)
def skill_guide(
    section: str = "all",
    lang: str | None = None,
) -> SkillGuideResult:
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

    response: SkillGuideResult = {
        "version": GUIDE_VERSION,
        "locale":  locale,
    }

    if section in ("triggers", "all"):
        response["triggers"] = cast(list[GuideTrigger], get_triggers(locale))

    if section in ("examples", "all"):
        response["examples"] = cast(list[GuideExample], get_examples(locale))

    if section in ("anti_patterns", "all"):
        response["anti_patterns"] = cast(list[GuideAntiPattern], get_anti_patterns(locale))

    if section in ("playbooks", "all"):
        response["playbooks"] = cast(list[GuidePlaybook], get_playbooks(locale))

    return response
