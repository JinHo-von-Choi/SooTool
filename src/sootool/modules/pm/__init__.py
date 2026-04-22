"""Project Management domain module.

Importing this package registers all PM tools in REGISTRY.

내부 자료형 및 캐스팅 정책 (ADR-008):
- EVM: 전 구간 Decimal (금액 계산).
- CPM: 기간(duration)은 Decimal, 위상 정렬은 stdlib graphlib.
- PERT: Decimal 입력/출력, sqrt는 mpmath 경유.
"""
from __future__ import annotations

from sootool.modules.pm import cpm, evm, pert

__all__ = ["cpm", "evm", "pert"]
