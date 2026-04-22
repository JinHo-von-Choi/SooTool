"""Confidence interval calculations.

Author: 최진호
Date: 2026-04-22

Internal dtype: float64 (scipy). Boundaries: Decimal strings.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import scipy.stats as scipy_stats

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.stats.descriptive import _to_float_array


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _ci_mean_from_array(
    arr:        np.ndarray,
    confidence: float,
) -> dict[str, str]:
    """Compute confidence interval for mean from a numpy array."""
    n      = len(arr)
    mean_  = float(np.mean(arr))
    se    = float(scipy_stats.sem(arr))
    df    = n - 1
    lower, upper = scipy_stats.t.interval(confidence, df=df, loc=mean_, scale=se)
    return {"lower": _fmt(float(lower)), "upper": _fmt(float(upper))}


@REGISTRY.tool(
    namespace="stats",
    name="ci_mean",
    description="표본 평균의 신뢰구간 계산 (t-분포 기반).",
    version="1.0.0",
)
def stats_ci_mean(
    values:     list[str],
    confidence: str = "0.95",
) -> dict[str, Any]:
    """Confidence interval for the sample mean using the t-distribution.

    Args:
        values:     표본 데이터 (Decimal string 목록)
        confidence: 신뢰 수준 (Decimal string, 기본 "0.95")

    Returns:
        {mean, lower, upper, trace}
    """
    trace = CalcTrace(
        tool="stats.ci_mean",
        formula="t-분포 기반 신뢰구간: mean ± t*(alpha/2, df) * se",
    )

    conf_val = float(confidence)
    if not (0 < conf_val < 1):
        raise InvalidInputError(
            f"confidence는 0~1 사이여야 합니다. 입력: {confidence!r}"
        )

    arr = _to_float_array(values)
    if len(arr) < 2:
        raise InvalidInputError(
            f"values는 2개 이상이어야 합니다. 입력: {len(arr)}개"
        )

    mean_  = float(np.mean(arr))
    ci     = _ci_mean_from_array(arr, conf_val)

    trace.input("values",     values)
    trace.input("confidence", confidence)
    trace.output({"mean": _fmt(mean_), **ci})

    return {
        "mean":  _fmt(mean_),
        "lower": ci["lower"],
        "upper": ci["upper"],
        "trace": trace.to_dict(),
    }
