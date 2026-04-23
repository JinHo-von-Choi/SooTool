"""Bootstrap confidence intervals (deterministic, seed-fixed).

Author: 최진호
Date: 2026-04-23

Deterministic: numpy.random.default_rng(seed) — 동일 seed/데이터면 동일 결과.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.stats.descriptive import _to_float_array

_StatFn = Callable[..., Any]
_STAT_FNS: dict[str, _StatFn] = {
    "mean":   np.mean,
    "median": np.median,
}


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


@REGISTRY.tool(
    namespace="stats",
    name="bootstrap_ci",
    description=(
        "평균·중앙값 Bootstrap 신뢰구간 (백분위수법, deterministic). "
        "seed 고정으로 재현성 보장."
    ),
    version="1.0.0",
)
def stats_bootstrap_ci(
    values:      list[str],
    statistic:   str   = "mean",
    confidence:  float = 0.95,
    n_resamples: int   = 1000,
    seed:        int   = 42,
) -> dict[str, Any]:
    """Bootstrap CI for mean or median.

    Args:
        values:      표본 (Decimal string 목록)
        statistic:   'mean' 또는 'median'
        confidence:  신뢰수준 (0, 1)
        n_resamples: 반복 횟수 (>=1000 권장)
        seed:        난수 seed (기본 42, deterministic=True)

    Returns:
        {statistic, n, point_estimate, ci_lower, ci_upper, confidence, trace}
    """
    trace = CalcTrace(
        tool="stats.bootstrap_ci",
        formula=(
            "resample with replacement n_resamples times, "
            "compute statistic each, take empirical percentiles"
        ),
    )

    if statistic not in _STAT_FNS:
        raise InvalidInputError(
            f"statistic은 {list(_STAT_FNS.keys())} 중 하나여야 합니다."
        )
    if not (0.0 < confidence < 1.0):
        raise InvalidInputError("confidence는 (0, 1) 범위여야 합니다.")
    if n_resamples < 100:
        raise InvalidInputError("n_resamples는 100 이상이어야 합니다.")

    arr = _to_float_array(values)
    if len(arr) < 2:
        raise InvalidInputError("values는 2개 이상 필요합니다.")

    fn = _STAT_FNS[statistic]

    rng = np.random.default_rng(seed)
    n   = len(arr)
    # Matrix resample: (n_resamples, n) indices
    idx = rng.integers(0, n, size=(n_resamples, n))
    samples = arr[idx]
    stats_arr = fn(samples, axis=1)

    point = float(fn(arr))
    alpha = 1.0 - confidence
    lo_q  = (alpha / 2.0) * 100.0
    hi_q  = (1.0 - alpha / 2.0) * 100.0
    lower = float(np.percentile(stats_arr, lo_q))
    upper = float(np.percentile(stats_arr, hi_q))

    trace.input("values_n",    n)
    trace.input("statistic",   statistic)
    trace.input("confidence",  confidence)
    trace.input("n_resamples", n_resamples)
    trace.input("seed",        seed)
    trace.output({"ci_lower": _fmt(lower), "ci_upper": _fmt(upper)})

    return {
        "statistic":      statistic,
        "n":              n,
        "point_estimate": _fmt(point),
        "ci_lower":       _fmt(lower),
        "ci_upper":       _fmt(upper),
        "confidence":     _fmt(confidence, 6),
        "n_resamples":    n_resamples,
        "seed":           seed,
        "trace":          trace.to_dict(),
    }
