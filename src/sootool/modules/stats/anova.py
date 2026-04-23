"""One-way ANOVA + Tukey HSD post-hoc.

Author: 최진호
Date: 2026-04-23

Internal dtype: float64 (scipy). Boundaries: Decimal strings.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import scipy.stats as stats

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.stats.descriptive import _to_float_array


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _tukey_hsd(
    groups: list[np.ndarray],
    alpha:  float,
) -> list[dict[str, Any]]:
    """Tukey HSD pairwise comparison (equal n assumed; otherwise Tukey-Kramer)."""
    k = len(groups)
    ns     = [len(g) for g in groups]
    means  = [float(np.mean(g)) for g in groups]

    # Pooled within-group mean square (MSE)
    dfs    = [n - 1 for n in ns]
    ssws   = [float(np.var(g, ddof=1)) * (n - 1) for g, n in zip(groups, ns, strict=True)]
    df_w   = int(sum(dfs))
    mse    = sum(ssws) / df_w if df_w > 0 else 0.0

    q_crit = float(stats.studentized_range.ppf(1 - alpha, k, df_w))

    pairs: list[dict[str, Any]] = []
    for i in range(k):
        for j in range(i + 1, k):
            mean_diff = means[i] - means[j]
            se = np.sqrt(mse * (1.0 / ns[i] + 1.0 / ns[j]) / 2.0)
            q_stat = abs(mean_diff) / se if se > 0.0 else 0.0
            # p-value via studentized_range SF
            p_val = float(stats.studentized_range.sf(q_stat, k, df_w))
            reject = bool(q_stat > q_crit)
            pairs.append({
                "group_i":   i,
                "group_j":   j,
                "mean_diff": _fmt(mean_diff),
                "q_stat":    _fmt(q_stat),
                "p_value":   _fmt(p_val),
                "reject_h0": reject,
            })
    return pairs


@REGISTRY.tool(
    namespace="stats",
    name="anova_oneway",
    description=(
        "일원분산분석(one-way ANOVA) + Tukey HSD 사후검정. "
        "집단 간 평균 차이 유의성을 F-통계량과 쌍별 비교로 검정."
    ),
    version="1.0.0",
)
def stats_anova_oneway(
    groups:        list[list[str]],
    alpha:         float = 0.05,
    include_tukey: bool  = True,
) -> dict[str, Any]:
    """One-way ANOVA with optional Tukey HSD.

    Args:
        groups:        집단별 표본(Decimal string 이중 리스트). 2개 이상 집단 필요.
        alpha:         유의수준 (기본 0.05)
        include_tukey: Tukey HSD 사후검정 포함 여부

    Returns:
        {f_stat, p_value, df_between, df_within, tukey_hsd(opt), trace}
    """
    trace = CalcTrace(
        tool="stats.anova_oneway",
        formula="scipy.stats.f_oneway + Tukey HSD",
    )

    if len(groups) < 2:
        raise InvalidInputError("groups는 2개 이상의 집단이어야 합니다.")
    if not (0.0 < alpha < 1.0):
        raise InvalidInputError("alpha는 (0, 1) 범위여야 합니다.")

    arrs = [_to_float_array(g) for g in groups]
    for idx, arr in enumerate(arrs):
        if len(arr) < 2:
            raise InvalidInputError(f"groups[{idx}]는 2개 이상 필요합니다.")

    f_stat, p_val = stats.f_oneway(*arrs)
    f_stat = float(f_stat)
    p_val  = float(p_val)

    k = len(arrs)
    n_total = sum(len(a) for a in arrs)
    df_between = k - 1
    df_within  = n_total - k

    trace.input("groups_n", [len(a) for a in arrs])
    trace.input("alpha",    alpha)
    trace.output({"f_stat": _fmt(f_stat), "p_value": _fmt(p_val)})

    result: dict[str, Any] = {
        "f_stat":     _fmt(f_stat, 6),
        "p_value":    _fmt(p_val),
        "df_between": df_between,
        "df_within":  df_within,
        "alpha":      _fmt(alpha, 6),
        "reject_h0":  bool(p_val < alpha),
        "trace":      trace.to_dict(),
    }

    if include_tukey:
        pairs = _tukey_hsd(arrs, alpha)
        result["tukey_hsd"] = pairs

    return result
