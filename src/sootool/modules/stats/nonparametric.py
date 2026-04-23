"""Non-parametric tests: Mann-Whitney U, Wilcoxon, Kruskal-Wallis.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from typing import Any

import scipy.stats as stats

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.stats.descriptive import _to_float_array

_ALT_MAP = {"two": "two-sided", "less": "less", "greater": "greater"}


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _validate_alt(tail: str) -> str:
    if tail not in _ALT_MAP:
        raise InvalidInputError("tail은 'two', 'less', 'greater' 중 하나여야 합니다.")
    return _ALT_MAP[tail]


@REGISTRY.tool(
    namespace="stats",
    name="mann_whitney_u",
    description=(
        "Mann-Whitney U 검정 (독립 두 표본, 순위합 비반복). "
        "정규성 가정 불필요."
    ),
    version="1.0.0",
)
def stats_mann_whitney_u(
    a:    list[str],
    b:    list[str],
    tail: str = "two",
) -> dict[str, Any]:
    """Mann-Whitney U test.

    Returns:
        {u_stat, p_value, n_a, n_b, trace}
    """
    trace = CalcTrace(
        tool="stats.mann_whitney_u",
        formula="scipy.stats.mannwhitneyu",
    )
    alt = _validate_alt(tail)

    arr_a = _to_float_array(a)
    arr_b = _to_float_array(b)
    if len(arr_a) < 1 or len(arr_b) < 1:
        raise InvalidInputError("a, b는 각각 1개 이상 필요합니다.")

    result = stats.mannwhitneyu(arr_a, arr_b, alternative=alt)
    u_stat = float(result.statistic)
    p_val  = float(result.pvalue)

    trace.input("a", a)
    trace.input("b", b)
    trace.input("tail", tail)
    trace.output({"u_stat": _fmt(u_stat), "p_value": _fmt(p_val)})

    return {
        "u_stat":  _fmt(u_stat, 6),
        "p_value": _fmt(p_val),
        "n_a":     len(arr_a),
        "n_b":     len(arr_b),
        "trace":   trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="stats",
    name="wilcoxon",
    description=(
        "Wilcoxon signed-rank test (대응 표본 또는 단일 표본 중앙값 검정)."
    ),
    version="1.0.0",
)
def stats_wilcoxon(
    a:    list[str],
    b:    list[str] | None = None,
    tail: str = "two",
) -> dict[str, Any]:
    """Wilcoxon signed-rank test.

    Args:
        a:    첫 번째 표본
        b:    대응 표본(옵션). None이면 a 자체의 중앙값 검정
        tail: 'two' | 'less' | 'greater'

    Returns:
        {w_stat, p_value, n, trace}
    """
    trace = CalcTrace(
        tool="stats.wilcoxon",
        formula="scipy.stats.wilcoxon",
    )
    alt = _validate_alt(tail)

    arr_a = _to_float_array(a)
    if b is None:
        if len(arr_a) < 1:
            raise InvalidInputError("a는 1개 이상 필요합니다.")
        result = stats.wilcoxon(arr_a, alternative=alt)
        n_used = len(arr_a)
    else:
        arr_b = _to_float_array(b)
        if len(arr_a) != len(arr_b):
            raise InvalidInputError("a와 b의 길이가 같아야 합니다.")
        if len(arr_a) < 1:
            raise InvalidInputError("표본 크기가 1 이상이어야 합니다.")
        result = stats.wilcoxon(arr_a, arr_b, alternative=alt)
        n_used = len(arr_a)

    w_stat = float(result.statistic)
    p_val  = float(result.pvalue)

    trace.input("a",    a)
    trace.input("b",    b)
    trace.input("tail", tail)
    trace.output({"w_stat": _fmt(w_stat), "p_value": _fmt(p_val)})

    return {
        "w_stat":  _fmt(w_stat, 6),
        "p_value": _fmt(p_val),
        "n":       n_used,
        "trace":   trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="stats",
    name="kruskal_wallis",
    description=(
        "Kruskal-Wallis H 검정 (3개 이상 독립 표본 순위합 검정)."
    ),
    version="1.0.0",
)
def stats_kruskal_wallis(
    groups: list[list[str]],
) -> dict[str, Any]:
    """Kruskal-Wallis H test.

    Returns:
        {h_stat, p_value, df, trace}
    """
    trace = CalcTrace(
        tool="stats.kruskal_wallis",
        formula="scipy.stats.kruskal",
    )
    if len(groups) < 2:
        raise InvalidInputError("groups는 2개 이상의 집단이어야 합니다.")

    arrs = [_to_float_array(g) for g in groups]
    for idx, arr in enumerate(arrs):
        if len(arr) < 1:
            raise InvalidInputError(f"groups[{idx}]는 1개 이상 필요합니다.")

    result = stats.kruskal(*arrs)
    h_stat = float(result.statistic)
    p_val  = float(result.pvalue)
    df     = len(arrs) - 1

    trace.input("groups_n", [len(a) for a in arrs])
    trace.output({"h_stat": _fmt(h_stat), "p_value": _fmt(p_val)})

    return {
        "h_stat":  _fmt(h_stat, 6),
        "p_value": _fmt(p_val),
        "df":      df,
        "trace":   trace.to_dict(),
    }
