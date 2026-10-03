"""도구 결과 스키마의 공통 구성 요소.

모든 도구 응답은 서버 후처리로 ``_meta``(영수증, 엔진, 힌트)가 붙고, 정책 기반 도구는 정책 출처 필드가
붙는다. 도구별 결과 타입은 여기의 기반 타입을 상속해 도구 고유 필드만 선언한다. 기반 타입은 선언하지
않은 키를 허용(``extra="allow"``)하므로 후처리가 키를 더해도 출력 검증에서 잘리지 않는다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import typing
from collections.abc import Callable
from typing import Any, NotRequired, TypedDict

from pydantic import ConfigDict, with_config

_OPEN = with_config(ConfigDict(extra="allow"))


class Hint(TypedDict):
    """에이전트용 후속 행동 제안."""

    signal:           str
    suggestion:       str
    recommended_tool: str | None


@_OPEN
class Integrity(TypedDict):
    """입력과 결과의 해시, 도구 버전, 정책 출처를 묶은 영수증."""

    tool:            str
    input_hash:      str
    result_hash:     str
    tool_version:    str
    sootool_version: str
    signature:       NotRequired[str]
    key_id:          NotRequired[str]


@_OPEN
class Meta(TypedDict):
    """서버가 응답에 붙이는 부가 정보. 계산 결과와 해시 대상에서 제외된다."""

    integrity:     NotRequired[Integrity]
    engine:        NotRequired[str]
    hints:         NotRequired[list[Hint]]
    session_stats: NotRequired[dict[str, Any]]


class TraceStep(TypedDict):
    label: str
    value: Any


class Trace(TypedDict):
    """계산 근거. ``steps`` 는 trace_level=full 일 때만 있다."""

    tool:    str
    formula: str
    inputs:  dict[str, Any]
    steps:   NotRequired[list[TraceStep]]
    output:  Any


@_OPEN
class Citation(TypedDict):
    law:     str
    article: NotRequired[str]
    url:     NotRequired[str]
    note:    NotRequired[str]


@_OPEN
class PolicyVersion(TypedDict):
    """적용된 정책 문서의 식별 정보."""

    year:           int
    sha256:         str
    effective_date: str
    effective_to:   str | None
    status:         str
    version:        str | None
    notice_no:      str
    source_url:     str
    citations:      list[Citation]
    reviewed_by:    list[str]


@_OPEN
class ToolResult(TypedDict):
    """모든 도구 결과의 기반. 후처리가 더하는 ``_meta`` 만 공통이다."""

    _meta: NotRequired[Meta]


@_OPEN
class TracedResult(ToolResult):
    """``trace`` 를 포함하는 계산 도구의 결과 기반."""

    trace: Trace


@_OPEN
class PolicyResult(TracedResult):
    """정책 문서를 읽는 도구의 결과 기반. 정책 출처가 평탄화되어 함께 반환된다."""

    policy_version:        PolicyVersion
    policy_source:         str
    policy_audit_id:       str | None
    policy_sha256:         str
    policy_effective_date: str
    policy_effective_to:   str | None
    policy_status:         str
    policy_citations:      list[Citation]


def declared_result_type(fn: Callable[..., Any]) -> Any | None:
    """도구 함수가 선언한 정밀 결과 타입. 범용 dict 나 Any 만 선언했으면 None."""
    try:
        returned = typing.get_type_hints(fn).get("return")
    except Exception:  # noqa: BLE001
        return None
    if returned is None or returned is Any or returned is dict or typing.get_origin(returned) is dict:
        return None
    return returned
