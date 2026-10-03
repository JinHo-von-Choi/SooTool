"""도구 메타데이터의 단일 조회 지점.

도구 정의(``ToolEntry``)와 거기서 파생되는 값(엔진, 정확도 등급, 별칭, 결과 타입 이름, 파라미터)을 한 구조로
묶는다. 검색 설명(``describe``), 문서 목록 생성, SDK 타입 선언이 같은 값을 쓰게 해 서로 어긋나지 않게 한다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Final

from sootool.core.engines import COMPOSITE, DECIMAL, FLOAT64, MPMATH, NONE, engine_of
from sootool.core.registry import ToolEntry
from sootool.core.result_types import declared_result_type
from sootool.core.tool_aliases import ALIASES

# 엔진별 정확도 등급. exact 는 Decimal 로 정확히 계산, high_precision 은 지정 자릿수(기본 50)의 임의 정밀도,
# approximate 는 float64 근사, depends_on_children 은 호출한 도구에 따르며, not_numeric 은 수치 계산이 아니다.
EXACTNESS: Final[dict[str, str]] = {
    DECIMAL:   "exact",
    MPMATH:    "high_precision",
    FLOAT64:   "approximate",
    COMPOSITE: "depends_on_children",
    NONE:      "not_numeric",
}


@dataclass(frozen=True)
class ParameterSpec:
    name:     str
    type:     str
    required: bool
    default:  Any = None


@dataclass(frozen=True)
class ToolSpec:
    full_name:   str
    namespace:   str
    name:        str
    description: str
    version:     str
    read_only:   bool
    destructive: bool
    idempotent:  bool
    policy:      bool
    deprecated:  dict[str, Any] | None
    engine:      str
    exactness:   str
    result_type: str | None
    aliases:     tuple[str, ...]
    parameters:  tuple[ParameterSpec, ...]


def tool_spec(entry: ToolEntry) -> ToolSpec:
    """도구 정의에서 모든 파생 메타데이터를 모아 반환한다."""
    engine   = engine_of(entry)
    declared = declared_result_type(entry.fn)
    parameters = tuple(
        ParameterSpec(
            name     = p.name,
            type     = "" if p.annotation is inspect.Parameter.empty else str(p.annotation),
            required = p.default is inspect.Parameter.empty,
            default  = None if p.default is inspect.Parameter.empty else p.default,
        )
        for p in entry.exposed_signature().parameters.values()
    )
    return ToolSpec(
        full_name   = entry.full_name,
        namespace   = entry.namespace,
        name        = entry.name,
        description = entry.description,
        version     = entry.version,
        read_only   = entry.read_only,
        destructive = entry.destructive,
        idempotent  = entry.idempotent,
        policy      = entry.policy,
        deprecated  = entry.deprecated,
        engine      = engine,
        exactness   = EXACTNESS[engine],
        result_type = None if declared is None else getattr(declared, "__name__", str(declared)),
        aliases     = ALIASES.get(entry.full_name, ()),
        parameters  = parameters,
    )
