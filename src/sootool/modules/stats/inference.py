"""Statistical inference: t-tests and chi-square tests.

Author: 최진호
Date: 2026-04-22

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
from sootool.modules.stats.ci import _ci_mean_from_array
from sootool.modules.stats.descriptive import _to_float_array


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _fmt_p(p: float) -> str:
    return float64_to_decimal_str(p, 10)


def _fmt_t(t: float) -> str:
    return float64_to_decimal_str(t, 6)


def _adjust_p(p: float, tail: str) -> float:
    """Adjust two-tailed p-value to one-tailed if needed."""
    if tail == "two":
        return p
    return p / 2.0


@REGISTRY.tool(
    namespace="stats",
    name="ttest_one_sample",
    description="일표본 t-검정 (vs 모집단 평균 비교).",
    version="1.0.0",
)
def stats_ttest_one_sample(
    values:  list[str],
    popmean: str,
    tail:    str = "two",
) -> dict[str, Any]:
    """One-sample t-test comparing sample mean against a known population mean.

    Args:
        values:  표본 데이터 (Decimal string 목록)
        popmean: 비교 모집단 평균 (Decimal string)
        tail:    검정 방향 ("two"|"less"|"greater")

    Returns:
        {t, df, p_value, ci_95, trace}
    """
    trace = CalcTrace(tool="stats.ttest_one_sample", formula="scipy.stats.ttest_1samp")

    if tail not in ("two", "less", "greater"):
        raise InvalidInputError(f"tail은 'two', 'less', 'greater' 중 하나여야 합니다. 입력: {tail!r}")

    arr  = _to_float_array(values)
    mu   = float(popmean)

    if len(arr) < 2:
        raise InvalidInputError(f"values는 2개 이상이어야 합니다. 입력: {len(arr)}개")

    alt_map = {"two": "two-sided", "less": "less", "greater": "greater"}
    result  = stats.ttest_1samp(arr, popmean=mu, alternative=alt_map[tail])
    t_stat  = float(result.statistic)
    df      = int(len(arr) - 1)
    p_val   = float(result.pvalue)

    ci = _ci_mean_from_array(arr, 0.95)

    trace.input("values",  values)
    trace.input("popmean", popmean)
    trace.input("tail",    tail)
    trace.output({"t": _fmt_t(t_stat), "p_value": _fmt_p(p_val)})

    return {
        "t":        _fmt_t(t_stat),
        "df":       df,
        "p_value":  _fmt_p(p_val),
        "ci_95":    ci,
        "trace":    trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="stats",
    name="ttest_two_sample",
    description="이표본 t-검정 (Welch 기본, 분산 동일성 옵션).",
    version="1.0.0",
)
def stats_ttest_two_sample(
    a:         list[str],
    b:         list[str],
    equal_var: bool = False,
    tail:      str  = "two",
) -> dict[str, Any]:
    """Two-sample t-test (Welch's by default).

    Args:
        a:         첫 번째 표본 (Decimal string 목록)
        b:         두 번째 표본 (Decimal string 목록)
        equal_var: True면 Student's t-test (등분산), False면 Welch's t-test
        tail:      검정 방향 ("two"|"less"|"greater")

    Returns:
        {t, df, p_value, ci_95, trace}
    """
    trace = CalcTrace(
        tool="stats.ttest_two_sample",
        formula="scipy.stats.ttest_ind (Welch 또는 Student)",
    )

    if tail not in ("two", "less", "greater"):
        raise InvalidInputError("tail은 'two', 'less', 'greater' 중 하나여야 합니다.")

    arr_a = _to_float_array(a)
    arr_b = _to_float_array(b)

    if len(arr_a) < 2 or len(arr_b) < 2:
        raise InvalidInputError("a, b 각각 2개 이상이어야 합니다.")

    alt_map = {"two": "two-sided", "less": "less", "greater": "greater"}
    result  = stats.ttest_ind(arr_a, arr_b, equal_var=equal_var, alternative=alt_map[tail])
    t_stat  = float(result.statistic)
    p_val   = float(result.pvalue)

    # df: Welch-Satterthwaite (fractional for unequal var)
    df_raw: float
    if equal_var:
        df_raw = float(len(arr_a) + len(arr_b) - 2)
        df_str = str(int(df_raw))
    else:
        df_raw = float(getattr(result, "df"))
        df_str = _fmt(df_raw, 6)

    # CI for difference of means
    mean_diff = float(np.mean(arr_a) - np.mean(arr_b))
    se_diff   = float(np.sqrt(np.var(arr_a, ddof=1)/len(arr_a) + np.var(arr_b, ddof=1)/len(arr_b)))
    df_ci     = df_raw
    t_crit    = float(stats.t.ppf(0.975, df=df_ci))
    ci = {
        "lower": _fmt(mean_diff - t_crit * se_diff),
        "upper": _fmt(mean_diff + t_crit * se_diff),
    }

    trace.input("a",         a)
    trace.input("b",         b)
    trace.input("equal_var", equal_var)
    trace.input("tail",      tail)
    trace.output({"t": _fmt_t(t_stat), "p_value": _fmt_p(p_val)})

    return {
        "t":       _fmt_t(t_stat),
        "df":      df_str,
        "p_value": _fmt_p(p_val),
        "ci_95":   ci,
        "trace":   trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="stats",
    name="ttest_paired",
    description="짝지은 t-검정 (대응표본, 전후 비교 등).",
    version="1.0.0",
)
def stats_ttest_paired(
    a:    list[str],
    b:    list[str],
    tail: str = "two",
) -> dict[str, Any]:
    """Paired t-test (matched samples).

    Args:
        a:    첫 번째 표본 (Decimal string 목록)
        b:    두 번째 표본 (Decimal string 목록, a와 동일 길이)
        tail: 검정 방향 ("two"|"less"|"greater")

    Returns:
        {t, df, p_value, ci_95, trace}
    """
    trace = CalcTrace(tool="stats.ttest_paired", formula="scipy.stats.ttest_rel")

    if tail not in ("two", "less", "greater"):
        raise InvalidInputError("tail은 'two', 'less', 'greater' 중 하나여야 합니다.")

    arr_a = _to_float_array(a)
    arr_b = _to_float_array(b)

    if len(arr_a) != len(arr_b):
        raise InvalidInputError(
            f"a, b의 길이가 같아야 합니다. a={len(arr_a)}, b={len(arr_b)}"
        )
    if len(arr_a) < 2:
        raise InvalidInputError("a, b 각각 2개 이상이어야 합니다.")

    alt_map = {"two": "two-sided", "less": "less", "greater": "greater"}
    result  = stats.ttest_rel(arr_a, arr_b, alternative=alt_map[tail])
    t_stat  = float(result.statistic)
    df      = int(len(arr_a) - 1)
    p_val   = float(result.pvalue)

    diff  = arr_a - arr_b
    ci    = _ci_mean_from_array(diff, 0.95)

    trace.input("a",    a)
    trace.input("b",    b)
    trace.input("tail", tail)
    trace.output({"t": _fmt_t(t_stat), "p_value": _fmt_p(p_val)})

    return {
        "t":       _fmt_t(t_stat),
        "df":      df,
        "p_value": _fmt_p(p_val),
        "ci_95":   ci,
        "trace":   trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="stats",
    name="chi_square_independence",
    description="카이제곱 독립성 검정 (분할표).",
    version="1.0.0",
)
def stats_chi_square_independence(
    observed: list[list[str]],
) -> dict[str, Any]:
    """Chi-square test of independence for a contingency table.

    Args:
        observed: 관측 빈도표 (list[list[str]], 2D Decimal string 행렬)

    Returns:
        {chi2, df, p_value, expected, trace}
    """
    trace = CalcTrace(
        tool="stats.chi_square_independence",
        formula="scipy.stats.chi2_contingency",
    )

    if not observed or not observed[0]:
        raise InvalidInputError("observed는 비어 있을 수 없습니다.")

    try:
        obs_arr = np.array([[float(v) for v in row] for row in observed], dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"observed를 숫자로 변환할 수 없습니다: {exc}") from exc

    if obs_arr.ndim != 2 or obs_arr.shape[0] < 2 or obs_arr.shape[1] < 2:
        raise InvalidInputError("observed는 최소 2x2 행렬이어야 합니다.")

    chi2_val, p_val, df_val, expected = stats.chi2_contingency(obs_arr)
    chi2_val = float(chi2_val)
    p_val    = float(p_val)
    df_val   = int(df_val)

    expected_str = [
        [_fmt(float(v)) for v in row]
        for row in expected
    ]

    trace.input("observed", observed)
    trace.output({"chi2": _fmt(chi2_val), "p_value": _fmt_p(p_val)})

    return {
        "chi2":     _fmt(chi2_val),
        "df":       df_val,
        "p_value":  _fmt_p(p_val),
        "expected": expected_str,
        "trace":    trace.to_dict(),
    }
