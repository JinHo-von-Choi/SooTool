"""도구 호출 단위 입력 한도의 단일 출처.

각 한도는 기본값을 코드에 두고, 환경변수 ``SOOTOOL_LIMIT_<이름>`` (양의 정수)으로
배포 환경에서 조정할 수 있다. 잘못된 환경변수 값은 무시하고 기본값을 쓴다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import os
from typing import Any, Final

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
    "SOLVER_EVALUATIONS":     200,
    "SCENARIOS":              50,
    "MATRIX_DIM":             200,
    "POLYNOMIAL_DEGREE":      256,
    "FFT_SAMPLES":            65_536,
    "CRYPTO_DIGITS":          2_048,
    "ARG_STRING_CHARS":       100_000,
    "ARG_LIST_ITEMS":         100_000,
    "ARG_DEPTH":              16,
    "ARG_NODES":              1_000_000,
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


def validate_argument_sizes(arguments: dict[str, Any]) -> None:
    """도구 인자 전체의 크기를 검사한다.

    문자열 길이, 목록·객체 원소 수, 중첩 깊이, 전체 노드 수가 한도를 넘으면 InputLimitError 를
    낸다. 도구별 한도(``ensure_max``)와 별개로 모든 호출 경로(stdio, 네트워크, 프로세스 내,
    batch 와 pipeline 의 중첩 호출)에 같은 상한을 적용해 처리량을 가장 바깥에서 묶는다.
    """
    max_string = limit("ARG_STRING_CHARS")
    max_items  = limit("ARG_LIST_ITEMS")
    max_depth  = limit("ARG_DEPTH")
    max_nodes  = limit("ARG_NODES")

    nodes = 0
    stack: list[tuple[str, Any, int]] = [(key, value, 1) for key, value in arguments.items()]
    while stack:
        path, value, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            raise InputLimitError("arguments", max_nodes, nodes)
        if isinstance(value, str):
            if len(value) > max_string:
                raise InputLimitError(path, max_string, len(value))
        elif isinstance(value, (list, tuple)):
            if depth > max_depth:
                raise InputLimitError(path, max_depth, depth)
            if len(value) > max_items:
                raise InputLimitError(path, max_items, len(value))
            child = f"{path}[]"
            stack.extend((child, item, depth + 1) for item in value)
        elif isinstance(value, dict):
            if depth > max_depth:
                raise InputLimitError(path, max_depth, depth)
            if len(value) > max_items:
                raise InputLimitError(path, max_items, len(value))
            stack.extend((f"{path}.{key}", item, depth + 1) for key, item in value.items())
