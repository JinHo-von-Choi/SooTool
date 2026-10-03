"""도구 호출 단위 입력 한도의 단일 출처.

각 한도는 기본값을 코드에 두고, 환경변수 ``SOOTOOL_LIMIT_<이름>`` (양의 정수)으로
배포 환경에서 조정할 수 있다. 잘못된 환경변수 값은 무시하고 기본값을 쓴다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import os
from typing import Final

from sootool.core.errors import InputLimitError

_DEFAULTS: Final[dict[str, int]] = {
    "COMBINATORICS_N":        20_000,
    "PRIME_ROUNDS":           256,
    "LOAN_MONTHS":            1_200,
    "MONTE_CARLO_TRIALS":     1_000_000,
    "BOOTSTRAP_RESAMPLES":    100_000,
    "SIMPSON_INTERVALS":      20_000,
    "GAUSS_LEGENDRE_DEGREE":  100,
    "BUSINESS_DAYS_SPAN":     100_000,
    "CALC_PRECISION":         10_000,
    "SOLVER_ITERATIONS":      10_000,
}


def limit(name: str) -> int:
    """이름에 해당하는 현재 한도를 반환한다. 미등록 이름은 KeyError."""
    default = _DEFAULTS[name]
    raw     = os.environ.get(f"SOOTOOL_LIMIT_{name}", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def ensure_max(name: str, value: int, field: str | None = None) -> None:
    """``abs(value)`` 가 한도 ``name`` 을 넘으면 InputLimitError 를 발생시킨다."""
    cap = limit(name)
    if abs(value) > cap:
        raise InputLimitError(field or name.lower(), cap, value)
