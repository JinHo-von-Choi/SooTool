"""Symbolic hybrid bridge domain module (ADR-022).

CE-M4 축소 하이브리드: sympy 기반 기호 해석 결과를 Decimal 경계로 재평가.

내부 자료형 및 캐스팅 정책:
- 입력 expression/equation은 core.calc 의 AST 화이트리스트를 선행 통과한다.
- sympy.sympify 는 locals={} 로 호출하여 네임스페이스 주입 경로를 봉쇄한다.
- sympy 결과는 sympy.Float 또는 기호 식으로 받고, 수치 평가 시 mpmath.mpf 경유
  Decimal 문자열로 직렬화한다. float 누수는 cast.mpmath_to_decimal 로 차단.
- 노출 도구 2종: symbolic.solve, symbolic.diff.

sympy 는 optional dependency 이며 `pip install 'sootool[symbolic]'` 로 설치한다.
미설치 상태에서 도구 호출 시 친절한 안내와 함께 ImportError 를 발생시킨다.

작성자: 최진호
작성일: 2026-04-24
"""
from __future__ import annotations

from sootool.modules.symbolic import diff, solve

__all__ = ["diff", "solve"]
