"""전체 시험 공통 설정.

도구 결과 계약: 도구 함수가 정밀 결과 타입을 선언했으면, 시험 중 REGISTRY.invoke 가 돌려주는 모든 결과를
그 타입으로 검증한다. 선언과 실제 응답이 어긋나면 해당 호출을 하는 어느 시험에서든 바로 실패한다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from sootool.core.registry import ToolRegistry
from sootool.core.result_types import declared_result_type

_ADAPTERS: dict[int, TypeAdapter[Any] | None] = {}


def _adapter(registry: ToolRegistry, full_name: str) -> TypeAdapter[Any] | None:
    entry = registry._tools.get(full_name)
    if entry is None:
        return None
    key = id(entry.fn)
    if key not in _ADAPTERS:
        declared = declared_result_type(entry.fn)
        _ADAPTERS[key] = TypeAdapter(declared) if declared is not None else None
    return _ADAPTERS[key]


@pytest.fixture(autouse=True, scope="session")
def _tool_results_match_declared_types():
    original = ToolRegistry.invoke

    def checked(self: ToolRegistry, full_name: str, **kwargs: Any) -> Any:
        result = original(self, full_name, **kwargs)
        adapter = _adapter(self, full_name)
        if adapter is not None:
            try:
                adapter.validate_python(result)
            except ValidationError as exc:
                raise AssertionError(f"{full_name} 결과가 선언한 타입과 다릅니다:\n{exc}") from exc
        return result

    ToolRegistry.invoke = checked  # type: ignore[method-assign]
    try:
        yield
    finally:
        ToolRegistry.invoke = original  # type: ignore[method-assign]
