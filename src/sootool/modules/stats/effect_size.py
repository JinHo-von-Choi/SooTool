"""Effect size: Cohen's d, Hedges's g, eta^2, omega^2.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.lazy import lazy_module
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.stats.descriptive import _to_float_array

stats = lazy_module("scipy.stats")


class StatsCohensDResult(TracedResult):
    d:        str
    hedges_g: str
    n_a:      int
    n_b:      int


class StatsEtaSquaredResult(TracedResult):
    eta_squared:   str
    omega_squared: str
    f_stat:        str
    p_value:       str
    df_between:    int
    df_within:     int


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


@REGISTRY.tool(
    namespace="stats",
    name="cohens_d",
    description=(
        "두 독립 표본의 효과크기 Cohen's d와 소표본 보정값 Hedges's g를 계산한다. "
        "d = (a 평균 - b 평균) / 풀드 표준편차이며 a 평균이 크면 양수다. a, b는 Decimal 문자열 각 2개 이상이고 "
        "풀드 표준편차가 0이면 오류다. 결과는 유효숫자 6자리 문자열이다. 대응표본(전후 비교)에는 쓰지 않는다."
    ),
    version="1.0.0",
)
def stats_cohens_d(
    a: list[str],
    b: list[str],
) -> StatsCohensDResult:
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
        raise InvalidInputError("풀드 표준편차가 0입니다, d 계산 불가.")

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
        "일원분산분석의 효과크기 eta^2(편향 있음)와 omega^2(편향 보정)를 계산하고 F, p값, 자유도도 함께 돌려준다. "
        "groups는 집단별 Decimal 문자열 목록이며 집단 2개 이상, 각 집단 2개 이상이다. "
        "eta^2 = SS_between / SS_total, 효과크기와 F는 유효숫자 6자리, p값은 10자리 문자열이다. "
        "표본이 작으면 eta^2가 과대 추정되므로 omega^2를 함께 본다."
    ),
    version="1.0.0",
)
def stats_eta_squared(
    groups: list[list[str]],
) -> StatsEtaSquaredResult:
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
