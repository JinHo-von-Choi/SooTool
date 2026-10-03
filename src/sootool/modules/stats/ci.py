"""Confidence interval calculations.

Author: 최진호
Date: 2026-04-22

Internal dtype: float64 (scipy). Boundaries: Decimal strings.
"""
from __future__ import annotations

from typing import TypedDict

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.lazy import lazy_module
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.stats.descriptive import _to_float_array

scipy_stats = lazy_module("scipy.stats")


class MeanInterval(TypedDict):
    lower: str
    upper: str


class StatsCiMeanResult(TracedResult):
    mean:  str
    lower: str
    upper: str


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _ci_mean_from_array(
    arr:        np.ndarray,
    confidence: float,
) -> MeanInterval:
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
    description=(
        "표본 평균의 양측 신뢰구간을 t-분포로 계산해 mean, lower, upper를 돌려준다. "
        "values는 Decimal 문자열 2개 이상, confidence는 0과 1 사이 Decimal 문자열(기본 \"0.95\")이다. "
        "표준오차는 표본 표준편차(ddof=1) 기반이며 float64 계산 결과를 유효숫자 10자리 문자열로 돌려준다. "
        "confidence에 95처럼 백분율을 넣으면 오류이고, 모집단 비율의 구간에는 쓸 수 없다."
    ),
    version="1.0.0",
)
def stats_ci_mean(
    values:     list[str],
    confidence: str = "0.95",
) -> StatsCiMeanResult:
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
