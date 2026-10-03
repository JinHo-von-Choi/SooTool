"""
core.calc: AST 기반 안전 수식 평가기.

ADR-017 (core.calc 보안 경계) 구현.

설계:
- ast.parse(mode="eval") + NodeVisitor 화이트리스트로 허용 노드만 통과.
- 순수 정수 사칙·모듈러·정수 지수 Pow는 Decimal 직접 연산.
- 초월 함수와 비정수 지수 Pow는 mpmath.mp.dps 로컬 컨텍스트로 계산 후
  core.cast.mpmath_to_decimal 을 경유해 Decimal 문자열로 복귀(ADR-008).
- Python eval/exec/compile 미사용. AST 평가만 수행.

구성: _rules(화이트리스트와 한도), _validate(파싱과 검증), _values(값 변환), _evaluator(평가기), api(calc).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from sootool.core.calc._validate import (  # noqa: F401
    _count_and_validate,
    _parse,
)
from sootool.core.calc.api import (  # noqa: F401
    calc,
)

__all__ = ["_count_and_validate", "_parse", "calc"]
