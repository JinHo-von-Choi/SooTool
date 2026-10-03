"""도구 카탈로그 검색·설명 (경량 프로파일 파사드의 공용 로직).

전체 도구 정의를 클라이언트 컨텍스트에 싣지 않고, 필요한 도구만 검색해 설명을 받고 호출하게
하는 progressive disclosure 경로를 제공한다. 순위는 결정적이다(점수 내림차순, 이름 오름차순).

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import inspect
import re
from typing import Any

from sootool.core.errors import InvalidInputError
from sootool.core.registry import ToolEntry, ToolRegistry
from sootool.core.tool_aliases import ALIASES
from sootool.core.toolspec import tool_spec

_TOKEN_RE        = re.compile(r"[0-9A-Za-z가-힣]+")
_SUMMARY_CHARS   = 120
_DEFAULT_LIMIT   = 10
_MAX_LIMIT       = 50
_SUGGESTION_SIZE = 3

_NAME_EXACT_SCORE     = 100
_NAME_TOKEN_SCORE     = 8
_NAME_SUBSTRING_SCORE = 4
_DESC_TOKEN_SCORE     = 2
_DESC_SUBSTRING_SCORE = 1
_ALIAS_EXACT_SCORE    = 50
_ALIAS_TOKEN_SCORE    = 6
_ALIAS_PHRASE_SCORE   = 10


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _alias_score(entry: ToolEntry, query: str, query_tokens: list[str]) -> int:
    """별칭 일치 점수. 별칭 전체 일치, 별칭 문구 포함, 토큰 일치를 순서대로 높게 본다."""
    score = 0
    for alias in ALIASES.get(entry.full_name, ()):
        text = alias.lower()
        if query == text:
            return _ALIAS_EXACT_SCORE
        if text in query or query in text:
            score += _ALIAS_PHRASE_SCORE
        alias_tokens = set(_tokens(text))
        score += _ALIAS_TOKEN_SCORE * sum(1 for tok in query_tokens if tok in alias_tokens)
    return score


def _score(entry: ToolEntry, query: str, query_tokens: list[str]) -> int:
    full_name = entry.full_name.lower()
    if full_name == query:
        return _NAME_EXACT_SCORE
    name_tokens = set(_tokens(entry.full_name))
    desc_lower  = entry.description.lower()
    desc_tokens = set(_tokens(entry.description))
    score = _alias_score(entry, query, query_tokens)
    for tok in query_tokens:
        if tok in name_tokens:
            score += _NAME_TOKEN_SCORE
        elif tok in full_name:
            score += _NAME_SUBSTRING_SCORE
        if tok in desc_tokens:
            score += _DESC_TOKEN_SCORE
        elif tok in desc_lower:
            score += _DESC_SUBSTRING_SCORE
    return score


def _summary(description: str) -> str:
    text = " ".join(description.split())
    return text if len(text) <= _SUMMARY_CHARS else text[: _SUMMARY_CHARS - 1] + "…"


def search_tools(
    registry:  ToolRegistry,
    query:     str,
    limit:     int        = _DEFAULT_LIMIT,
    namespace: str | None = None,
) -> list[dict[str, Any]]:
    """질의와 관련된 도구를 점수 순으로 반환한다. 점수가 0인 도구는 제외한다."""
    if not isinstance(query, str) or not query.strip():
        raise InvalidInputError("query 는 비어 있지 않은 문자열이어야 합니다.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= _MAX_LIMIT:
        raise InvalidInputError(f"limit 는 1 이상 {_MAX_LIMIT} 이하의 정수여야 합니다: {limit!r}")

    normalized   = query.strip().lower()
    query_tokens = _tokens(normalized)
    ranked: list[tuple[int, ToolEntry]] = []
    for entry in registry.list():
        if namespace is not None and entry.namespace != namespace:
            continue
        score = _score(entry, normalized, query_tokens)
        if score > 0:
            ranked.append((score, entry))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].full_name))
    return [
        {
            "name":        entry.full_name,
            "summary":     _summary(entry.description),
            "read_only":   entry.read_only,
            "score":       score,
        }
        for score, entry in ranked[:limit]
    ]


def _json_safe_default(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def describe_tool(entry: ToolEntry) -> dict[str, Any]:
    """도구의 전체 설명, 동작 특성, 파라미터 목록, 독스트링을 반환한다."""
    spec = tool_spec(entry)
    parameters = []
    for param in spec.parameters:
        item: dict[str, Any] = {"name": param.name, "type": param.type, "required": param.required}
        if not param.required:
            item["default"] = _json_safe_default(param.default)
        parameters.append(item)
    return {
        "name":        spec.full_name,
        "description": spec.description,
        "version":     spec.version,
        "read_only":   spec.read_only,
        "destructive": spec.destructive,
        "idempotent":  spec.idempotent,
        "engine":      spec.engine,
        "exactness":   spec.exactness,
        "parameters":  parameters,
        "doc":         inspect.getdoc(entry.fn) or "",
    }


def resolve_tool(registry: ToolRegistry, name: str) -> ToolEntry:
    """이름으로 도구를 찾는다. 없으면 유사 후보를 포함한 InvalidInputError 를 낸다."""
    if not isinstance(name, str) or not name.strip():
        raise InvalidInputError("name 은 비어 있지 않은 문자열이어야 합니다.")
    for entry in registry.list():
        if entry.full_name == name:
            return entry
    suggestions = [hit["name"] for hit in search_tools(registry, name, limit=_SUGGESTION_SIZE)] \
        if _tokens(name) else []
    hint = f" 후보: {', '.join(suggestions)}" if suggestions else ""
    raise InvalidInputError(f"알 수 없는 도구입니다: {name!r}.{hint}")


def bind_call_arguments(entry: ToolEntry, arguments: dict[str, Any] | None) -> dict[str, Any]:
    """호출 인자가 도구 시그니처에 맞는지 확인하고 인자 사본을 반환한다."""
    kwargs = dict(arguments or {})
    try:
        entry.exposed_signature().bind(**kwargs)
    except TypeError as exc:
        raise InvalidInputError(
            f"{entry.full_name} 인자가 올바르지 않습니다: {exc}. sootool.describe 로 파라미터를 확인하세요."
        ) from exc
    return kwargs
