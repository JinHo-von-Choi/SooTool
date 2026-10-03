"""무거운 선택적 의존 모듈의 지연 로딩.

scipy.stats, statsmodels 처럼 임포트 비용이 큰 모듈을 서버 기동 시점이 아니라 해당 도구를
처음 호출할 때 불러온다. MCP 클라이언트의 stdio 기동 대기 시간을 줄이는 것이 목적이다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import importlib
from typing import Any


class _LazyModule:
    """첫 속성 접근 시 실제 모듈을 임포트하는 프록시."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __getattr__(self, attr: str) -> Any:
        return getattr(importlib.import_module(self._name), attr)

    def __repr__(self) -> str:
        return f"<lazy module {self._name!r}>"


def lazy_module(name: str) -> Any:
    """모듈 이름에 대한 지연 로딩 프록시를 반환한다.

    importlib.import_module 이 임포트 잠금과 sys.modules 캐시를 처리하므로 여러 스레드가
    동시에 처음 접근해도 안전하며, 이후 호출은 캐시된 모듈 조회 비용만 든다.
    """
    return _LazyModule(name)
