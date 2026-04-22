"""Descriptive statistics.

Author: 최진호
Date: 2026-04-22

Internal dtype: float64 (numpy). Boundaries: Decimal strings.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _to_float_array(values: list[str]) -> np.ndarray:
    """Convert list[str] Decimal strings to np.float64 array."""
    try:
        return np.array([float(v) for v in values], dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"values를 숫자로 변환할 수 없습니다: {exc}") from exc


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


@REGISTRY.tool(
    namespace="stats",
    name="descriptive",
    description="기술통계량 계산 (n, mean, median, variance, stdev, min, max, q1, q3).",
    version="1.0.0",
)
def stats_descriptive(
    values: list[str],
    ddof:   int = 1,
) -> dict[str, Any]:
    """Compute summary statistics for a list of numeric Decimal strings.

    Args:
        values: 숫자 Decimal 문자열 목록
        ddof:   분산/표준편차 자유도 보정 (기본 1 = 표본, 0 = 모집단)

    Returns:
        {n, mean, median, variance, stdev, min, max, q1, q3, trace}
    """
    trace = CalcTrace(tool="stats.descriptive", formula="numpy 기술통계")

    if len(values) < 2:
        raise InvalidInputError(
            f"values는 2개 이상이어야 합니다. 입력: {len(values)}개"
        )

    arr = _to_float_array(values)
    n   = len(arr)

    mean_   = float(np.mean(arr))
    median_ = float(np.median(arr))
    var_    = float(np.var(arr, ddof=ddof))
    std_    = float(np.std(arr, ddof=ddof))
    min_    = float(np.min(arr))
    max_    = float(np.max(arr))
    q1_     = float(np.percentile(arr, 25))
    q3_     = float(np.percentile(arr, 75))

    trace.input("values", values)
    trace.input("ddof",   ddof)
    trace.output({"mean": _fmt(mean_), "stdev": _fmt(std_)})

    return {
        "n":        n,
        "mean":     _fmt(mean_),
        "median":   _fmt(median_),
        "variance": _fmt(var_),
        "stdev":    _fmt(std_),
        "min":      _fmt(min_),
        "max":      _fmt(max_),
        "q1":       _fmt(q1_),
        "q3":       _fmt(q3_),
        "trace":    trace.to_dict(),
    }
