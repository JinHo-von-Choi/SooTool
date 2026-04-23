"""Math numerical analysis domain module.

Importing this package registers all math tools in REGISTRY.

내부 자료형 및 캐스팅 정책 (ADR-008):
- integration: mpmath 기반 수치 적분. Decimal 경계 입출력.
- differentiation: 중심 차분·5점 공식, 내부 float64, Decimal 문자열 출력.
- interpolation: numpy 1D 선형·3차 스플라인, float64 내부, Decimal 출력.
- polynomial: numpy.roots + 호너 평가, float64/Decimal 이원화.
- fft: numpy.fft 이산 푸리에 변환, 복소수는 (magnitude, phase) Decimal 쌍으로 직렬화.
"""
from __future__ import annotations

from sootool.modules.math import (
    differentiation,
    fft,
    integration,
    interpolation,
    polynomial,
)

__all__ = ["differentiation", "fft", "integration", "interpolation", "polynomial"]
