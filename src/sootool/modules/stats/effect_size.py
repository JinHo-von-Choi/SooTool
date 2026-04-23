"""Effect size: Cohen's d, Hedges's g, eta^2, omega^2.

Author: 최진호
Date: 2026-04-23
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


@REGISTRY.tool(
    namespace="stats",
    name="cohens_d",
    description=(
        "Cohen's d (두 독립 표본 효과크기). "
        "풀드 표준편차 기반. Hedges's g 보정계수도 함께 반환."
    ),
    version="1.0.0",
)
def stats_cohens_d(
    a: list[str],
    b: list[str],
) -> dict[str, Any]:
    """Cohen's d + Hedges's g.

    d = (mean_a - mean_b) / s_pooled
    g = d * (1 - 3 / (4*(n_a+n_b) - 9))

    Returns:
        {d, hedges_g, n_a, n_b, trace}
    """
    trace = CalcTrace(
        tool="stats.cohens_d",
        formula="d = (mean_a - mean_b) / s_pooled; g = d * J",
    )
    arr_a = _to_float_array(a)
    arr_b = _to_float_array(b)
    if len(arr_a) < 2 or len(arr_b) < 2:
        raise InvalidInputError("a, b는 각각 2개 이상 필요합니다.")

    n_a = len(arr_a)
    n_b = len(arr_b)
    mean_a = float(np.mean(arr_a))
    mean_b = float(np.mean(arr_b))
    var_a  = float(np.var(arr_a, ddof=1))
    var_b  = float(np.var(arr_b, ddof=1))

    pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
    s_pooled   = float(np.sqrt(pooled_var))
    if s_pooled == 0.0:
        raise InvalidInputError("풀드 표준편차가 0입니다 — d 계산 불가.")

    d = (mean_a - mean_b) / s_pooled
    # Hedges correction factor J
    j = 1.0 - (3.0 / (4.0 * (n_a + n_b) - 9.0))
    g = d * j

    trace.input("a", a)
    trace.input("b", b)
    trace.output({"d": _fmt(d), "hedges_g": _fmt(g)})

    return {
        "d":         _fmt(d, 6),
        "hedges_g":  _fmt(g, 6),
        "n_a":       n_a,
        "n_b":       n_b,
        "trace":     trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="stats",
    name="eta_squared",
    description=(
        "ANOVA 효과크기: eta^2 (편향됨), omega^2 (편향보정). "
        "집단별 표본 입력."
    ),
    version="1.0.0",
)
def stats_eta_squared(
    groups: list[list[str]],
) -> dict[str, Any]:
    """Compute eta^2 and omega^2 for one-way ANOVA.

    eta^2   = SS_between / SS_total
    omega^2 = (SS_between - (k-1)*MSE) / (SS_total + MSE)
    """
    trace = CalcTrace(
        tool="stats.eta_squared",
        formula="eta^2 = SSB/SST; omega^2 = (SSB - (k-1)*MSE)/(SST + MSE)",
    )
    if len(groups) < 2:
        raise InvalidInputError("groups는 2개 이상 필요합니다.")

    arrs = [_to_float_array(g) for g in groups]
    for idx, arr in enumerate(arrs):
        if len(arr) < 2:
            raise InvalidInputError(f"groups[{idx}]는 2개 이상 필요합니다.")

    all_values = np.concatenate(arrs)
    grand_mean = float(np.mean(all_values))
    n_total    = len(all_values)
    k          = len(arrs)

    # SS_between
    ss_between = sum(
        len(arr) * (float(np.mean(arr)) - grand_mean) ** 2
        for arr in arrs
    )
    # SS_within
    ss_within = sum(
        float(np.sum((arr - float(np.mean(arr))) ** 2))
        for arr in arrs
    )
    ss_total = ss_between + ss_within
    df_within = n_total - k
    mse = ss_within / df_within if df_within > 0 else 0.0

    eta2 = ss_between / ss_total if ss_total > 0.0 else 0.0
    omega2 = (
        (ss_between - (k - 1) * mse) / (ss_total + mse)
        if (ss_total + mse) > 0.0 else 0.0
    )

    # F statistic for reference
    df_between = k - 1
    f_stat, p_val = stats.f_oneway(*arrs)

    trace.input("groups_n", [len(a) for a in arrs])
    trace.output({"eta_squared": _fmt(eta2), "omega_squared": _fmt(omega2)})

    return {
        "eta_squared":   _fmt(eta2, 6),
        "omega_squared": _fmt(omega2, 6),
        "f_stat":        _fmt(float(f_stat), 6),
        "p_value":       _fmt(float(p_val)),
        "df_between":    df_between,
        "df_within":     df_within,
        "trace":         trace.to_dict(),
    }
