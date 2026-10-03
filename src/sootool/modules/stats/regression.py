"""Linear regression (OLS) with numpy and scipy.

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

Internal dtype: float64 (numpy/scipy). Boundaries: Decimal strings.
계수는 의사역행렬(pinv)로 구하고, 표준오차와 p값은 잔차 자유도 n - rank 의 t 분포로 계산한다.
결정계수는 상수항이 있으면 중심화 총제곱합, 없으면 비중심화 총제곱합을 쓴다.
"""
from __future__ import annotations

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.lazy import lazy_module
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

stats = lazy_module("scipy.stats")


class _OlsFit:
    """OLS 적합 결과(float64)."""

    __slots__ = ("params", "pvalues", "resid", "rsquared")

    def __init__(self, params: np.ndarray, pvalues: np.ndarray, resid: np.ndarray, rsquared: float) -> None:
        self.params   = params
        self.pvalues  = pvalues
        self.resid    = resid
        self.rsquared = rsquared


def _has_constant(X: np.ndarray) -> bool:
    """설계행렬에 상수항(상수 열 또는 열들의 일차결합으로 표현되는 상수)이 있는지 판정한다."""
    if np.any(np.ptp(X, axis=0) == 0):
        return True
    ones = np.ones((X.shape[0], 1))
    return int(np.linalg.matrix_rank(np.hstack([ones, X]))) == int(np.linalg.matrix_rank(X))


def _ols(X: np.ndarray, y: np.ndarray) -> _OlsFit:
    pinv      = np.linalg.pinv(X)
    params    = pinv @ y
    resid     = y - X @ params
    rank      = int(np.linalg.matrix_rank(X))
    df_resid  = X.shape[0] - rank
    ssr       = float(resid @ resid)
    centered  = _has_constant(X)
    tss       = float(((y - y.mean()) ** 2).sum()) if centered else float(y @ y)
    with np.errstate(divide="ignore", invalid="ignore"):
        rsquared = float(1.0 - np.float64(ssr) / tss)
        sigma2   = np.float64(ssr) / df_resid
        bse      = np.sqrt(np.diag(pinv @ pinv.T) * sigma2)
        tvalues  = params / bse
        pvalues  = 2.0 * stats.t.sf(np.abs(tvalues), df_resid)
    return _OlsFit(params, pvalues, resid, rsquared)


class StatsRegressionLinearResult(TracedResult):
    coefficients: list[str]
    intercept:    str
    r_squared:    str
    p_values:     list[str]
    residuals:    list[str]


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _fmt_p(p: float) -> str:
    return float64_to_decimal_str(p, 10)


@REGISTRY.tool(
    namespace="stats",
    name="regression_linear",
    description=(
        "최소제곱(OLS) 선형회귀로 계수, 절편, R², 계수별 p값, 잔차를 구한다. "
        "X는 표본 수 x 특징 수의 Decimal 문자열 행렬, y는 표본 수 길이의 목록이며 표본 수는 특징 수 + 절편 수보다 커야 한다. "
        "add_intercept 기본 True이고 False면 절편은 \"0\"이다. p_values는 절편을 제외한 계수 순서이며 "
        "float64 계산 결과를 유효숫자 10자리 문자열로 돌려준다. 범주형 변수는 수치로 부호화해 넣어야 한다."
    ),
    version="1.0.0",
)
def stats_regression_linear(
    X:             list[list[str]],
    y:             list[str],
    add_intercept: bool = True,
) -> StatsRegressionLinearResult:
    """Ordinary Least Squares linear regression.

    Args:
        X:             입력 특징 행렬 (n_samples x n_features, Decimal string)
        y:             목표 벡터 (n_samples, Decimal string)
        add_intercept: True면 절편 추가 (기본 True)

    Returns:
        {coefficients, intercept, r_squared, p_values, residuals, trace}
    """
    trace = CalcTrace(
        tool="stats.regression_linear",
        formula="OLS: y = X*β + ε",
    )

    if not X or not y:
        raise InvalidInputError("X와 y는 비어 있을 수 없습니다.")

    n_samples = len(y)
    if len(X) != n_samples:
        raise InvalidInputError(
            f"X 행 수({len(X)})와 y 길이({n_samples})가 일치해야 합니다."
        )

    try:
        X_arr = np.array([[float(v) for v in row] for row in X], dtype=np.float64)
        y_arr = np.array([float(v) for v in y], dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"데이터를 숫자로 변환할 수 없습니다: {exc}") from exc

    if X_arr.ndim != 2:
        raise InvalidInputError("X는 2차원 행렬이어야 합니다.")

    n_features = X_arr.shape[1]

    if n_samples < n_features + (1 if add_intercept else 0) + 1:
        raise InvalidInputError(
            f"샘플 수({n_samples})가 특징 수({n_features}) + 절편보다 많아야 합니다."
        )

    X_fit = np.hstack([np.ones((n_samples, 1)), X_arr]) if add_intercept else X_arr

    results = _ols(X_fit, y_arr)

    params    = results.params
    p_values  = results.pvalues
    residuals = list(results.resid)

    if add_intercept:
        intercept_val = float(params[0])
        coef_vals     = [float(p) for p in params[1:]]
        p_coef        = [float(p) for p in p_values[1:]]
    else:
        intercept_val = 0.0
        coef_vals     = [float(p) for p in params]
        p_coef        = [float(p) for p in p_values]

    r_squared = results.rsquared

    trace.input("X",             X)
    trace.input("y",             y)
    trace.input("add_intercept", add_intercept)
    trace.output({"r_squared": _fmt(r_squared), "coefficients": [_fmt(c) for c in coef_vals]})

    return {
        "coefficients": [_fmt(c) for c in coef_vals],
        "intercept":    _fmt(intercept_val),
        "r_squared":    _fmt(r_squared),
        "p_values":     [_fmt_p(p) for p in p_coef],
        "residuals":    [_fmt(float(r)) for r in residuals],
        "trace":        trace.to_dict(),
    }
