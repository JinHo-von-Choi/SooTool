"""Science domain module.

Importing this package registers all science tools in REGISTRY.

내부 자료형 및 캐스팅 정책 (ADR-008):
- 화학(chemistry): 원소 개수는 정수, 원자량은 Decimal, 결과 Decimal.
- 물리(physics/half_life): Decimal 입출력, 지수 연산은 mpmath 경유.
- 열역학(thermo/ideal_gas): 전 구간 Decimal (PV=nRT).
"""
from __future__ import annotations

from sootool.modules.science import chemistry, physics, thermo

__all__ = ["chemistry", "physics", "thermo"]
