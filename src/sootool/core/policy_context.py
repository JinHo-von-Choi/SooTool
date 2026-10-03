"""정책 해석 컨텍스트: 시점(as_of)과 개정안 포함 여부.

정책 대상 도구 호출에 ``as_of`` 또는 ``include_proposed`` 가 지정되면 레지스트리가 호출이
끝날 때까지 이 값을 설정하고, 정책 로더가 같은 호출 안의 모든 정책 로드에 적용한다. 값이 없으면
기존 동작(연도별 최신 확정 버전)이다. 중첩 호출(batch, pipeline, 도구 안의 다른 도구 호출)은
컨텍스트를 상속한다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date

POLICY_AS_OF:           ContextVar[date | None] = ContextVar("sootool_policy_as_of", default=None)
POLICY_INCLUDE_PROPOSED: ContextVar[bool]       = ContextVar("sootool_policy_include_proposed", default=False)


@contextmanager
def policy_context(*, as_of: date | None, include_proposed: bool) -> Iterator[None]:
    """호출 범위의 정책 해석 컨텍스트를 설정하고 종료 시 복원한다."""
    tokens = (POLICY_AS_OF.set(as_of), POLICY_INCLUDE_PROPOSED.set(include_proposed))
    try:
        yield
    finally:
        POLICY_INCLUDE_PROPOSED.reset(tokens[1])
        POLICY_AS_OF.reset(tokens[0])
