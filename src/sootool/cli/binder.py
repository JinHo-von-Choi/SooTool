"""CLI 인자를 도구 시그니처에 맞춰 변환하고 검증한다.

MCP 경계와 같은 규칙을 쓴다: 문자열 숫자 파라미터는 JSON 숫자도 받고(``boundary._coercible``), 검증 실패는 같은
오류 계약(``invalid_arguments``)으로 보고한다. 숫자 문자열은 Decimal 경계를 위해 문자열 그대로 둔다.
"""
from __future__ import annotations

import json
import typing
from typing import Any

from pydantic import TypeAdapter, ValidationError

from sootool.boundary import _coercible, _validation_problems
from sootool.core.errors import InvalidArgumentsError, InvalidInputError
from sootool.core.registry import POLICY_PARAMETERS, ToolEntry


def _hints(entry: ToolEntry) -> dict[str, Any]:
    hints = typing.get_type_hints(entry.fn)
    for param in POLICY_PARAMETERS:
        if entry.policy:
            hints[param.name] = param.annotation
    return hints


def parse_assignment(entry: ToolEntry, assignment: str) -> tuple[str, Any]:
    """``이름=값`` 을 읽는다. 문자열 파라미터는 값을 그대로, 그 밖의 타입은 JSON 으로 해석한다."""
    name, separator, raw = assignment.partition("=")
    if not separator or not name:
        raise InvalidInputError(f"--arg 는 이름=값 형식이어야 합니다: {assignment!r}")
    hint = _hints(entry).get(name)
    if hint is None:
        raise InvalidArgumentsError([{"field": name, "message": "Unexpected argument"}])
    adapter_target = _coercible(hint)
    # 문자열로 해석 가능한 타입(str, str | None)은 값을 그대로 쓴다. 그 밖에는 JSON 을 시도한다.
    try:
        return name, TypeAdapter(adapter_target).validate_python(raw)
    except ValidationError:
        pass
    try:
        return name, json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"{name} 값을 해석할 수 없습니다(JSON 필요): {raw!r}") from exc


def bind_arguments(entry: ToolEntry, raw: dict[str, Any]) -> dict[str, Any]:
    """도구 인자 전체를 검증하고 변환한다. 실패하면 InvalidArgumentsError."""
    hints  = _hints(entry)
    signature = entry.exposed_signature()
    problems: list[dict[str, str]] = []
    bound: dict[str, Any] = {}

    for name in sorted(set(raw) - set(signature.parameters)):
        problems.append({"field": name, "message": "Unexpected argument"})
    for name, value in raw.items():
        if name not in signature.parameters:
            continue
        try:
            bound[name] = TypeAdapter(_coercible(hints.get(name, Any))).validate_python(value)
        except ValidationError as exc:
            for problem in _validation_problems(exc):
                field = name if problem["field"] == "(root)" else f"{name}.{problem['field']}"
                problems.append({"field": field, "message": problem["message"]})
    for name, param in signature.parameters.items():
        if param.default is param.empty and name not in raw:
            problems.append({"field": name, "message": "Field required"})
    if problems:
        raise InvalidArgumentsError(problems)
    return bound
