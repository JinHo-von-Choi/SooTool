"""Linear regression using statsmodels OLS.

Author: 최진호
Date: 2026-04-22

Internal dtype: float64 (statsmodels/numpy). Boundaries: Decimal strings.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import statsmodels.api as sm

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _fmt(x: float, digits: int = 10) -> str:
    return float64_to_decimal_str(x, digits)


def _fmt_p(p: float) -> str:
    return float64_to_decimal_str(p, 10)


@REGISTRY.tool(
    namespace="stats",
    name="regression_linear",
    description=(
        "선형회귀 (OLS). X: n_samples x n_features, y: n_samples. "
        "계수, 절편, R², p-values, 잔차 반환."
    ),
    version="1.0.0",
)
def stats_regression_linear(
    X:             list[list[str]],
    y:             list[str],
    add_intercept: bool = True,
) -> dict[str, Any]:
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
        formula="statsmodels OLS: y = X*β + ε",
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

    if add_intercept:
        X_fit = sm.add_constant(X_arr, has_constant="add")
    else:
        X_fit = X_arr

    model   = sm.OLS(y_arr, X_fit)
    results = model.fit()

    params   = results.params
    p_values = results.pvalues
    residuals = list(results.resid)

    if add_intercept:
        intercept_val = float(params[0])
        coef_vals     = [float(p) for p in params[1:]]
        p_coef        = [float(p) for p in p_values[1:]]
    else:
        intercept_val = 0.0
        coef_vals     = [float(p) for p in params]
        p_coef        = [float(p) for p in p_values]

    r_squared = float(results.rsquared)

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
