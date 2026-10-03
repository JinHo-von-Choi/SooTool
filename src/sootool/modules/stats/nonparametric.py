"""Non-parametric tests: Mann-Whitney U, Wilcoxon, Kruskal-Wallis.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.lazy import lazy_module
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.stats.descriptive import _to_float_array

stats = lazy_module("scipy.stats")

_ALT_MAP = {"two": "two-sided", "less": "less", "greater": "greater"}


class StatsMannWhitneyUResult(TracedResult):
    u_stat:  str
    p_value: str
    n_a:     int
    n_b:     int


class StatsWilcoxonResult(TracedResult):
    w_stat:  str
    p_value: str
    n:       int


class StatsKruskalWallisResult(TracedResult):
    h_stat:  str
    p_value: str
    df:      int


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
        "독립 두 표본의 분포 위치 차이를 순위 기반 Mann-Whitney U 검정으로 판정해 u_stat, p_value, n_a, n_b를 돌려준다. "
        "a, b는 Decimal 문자열 각 1개 이상, tail은 two(기본), less, greater이며 u_stat은 a 표본 기준이다. "
        "정규성 가정이 필요 없고 u는 유효숫자 6자리, p값은 10자리 문자열이다. 같은 대상의 전후 측정에는 wilcoxon 을 쓴다."
    ),
    version="1.0.0",
)
def stats_mann_whitney_u(
    a:    list[str],
    b:    list[str],
    tail: str = "two",
) -> StatsMannWhitneyUResult:
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
        "Wilcoxon 부호순위 검정으로 대응표본의 차이 또는 단일 표본의 0 기준 위치 이동을 판정해 w_stat, p_value, n을 돌려준다. "
        "b를 주면 a와 b는 같은 길이(1개 이상)의 짝지은 Decimal 문자열 목록이고, b를 생략하면 a 자체를 차이값으로 보고 0과 비교한다. "
        "tail은 two(기본), less, greater. w는 유효숫자 6자리, p값은 10자리 문자열이다. 독립 두 집단에는 mann_whitney_u 를 쓴다."
    ),
    version="1.0.0",
)
def stats_wilcoxon(
    a:    list[str],
    b:    list[str] | None = None,
    tail: str = "two",
) -> StatsWilcoxonResult:
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
        "독립 여러 집단의 분포 위치 차이를 순위 기반 Kruskal-Wallis H 검정으로 판정해 h_stat, p_value, df(집단 수-1)를 돌려준다. "
        "groups는 집단별 Decimal 문자열 목록이며 집단 2개 이상, 각 집단 1개 이상이다. "
        "정규성 가정이 필요 없고 H는 유효숫자 6자리, p값은 10자리 문자열이다. 사후 쌍별 비교는 제공하지 않는다."
    ),
    version="1.0.0",
)
def stats_kruskal_wallis(
    groups: list[list[str]],
) -> StatsKruskalWallisResult:
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
