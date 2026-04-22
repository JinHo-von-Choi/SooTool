"""Probability domain module.

Importing this package registers all probability tools in REGISTRY.

내부 자료형 및 캐스팅 정책 (ADR-008):
- 조합론(combinatorics): 정수 연산, 결과는 str 직렬화.
  n < 1000은 math.factorial, 그 이상은 mpmath.factorial.
- 베이즈(Bayes): Decimal 경계 입력/출력, 내부 연산 Decimal.
- 분포(distributions): scipy.stats 내부 float64, cast.float64_to_decimal_str로 출력.
- 기댓값(expected_value): Decimal 입력, Decimal 합산.
"""
from __future__ import annotations

from sootool.modules.probability import bayes, combinatorics, distributions, expected

__all__ = ["bayes", "combinatorics", "distributions", "expected"]
