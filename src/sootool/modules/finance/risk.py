"""Risk metrics: VaR (historical/parametric), CVaR, Sharpe, Sortino.

Author: 최진호
Date: 2026-04-23

All boundaries Decimal; internals use numpy/scipy. (ADR-008: finance is Decimal)
Rounded to 8 decimals on output.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import numpy as np
import scipy.stats as stats

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _to_decimal_array(values: list[str]) -> list[Decimal]:
    return [D(v) for v in values]


def _mean_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    total = sum(values, Decimal("0"))
    return total / Decimal(len(values))


def _stdev_decimal(values: list[Decimal], mean: Decimal, ddof: int = 1) -> Decimal:
    """Sample stdev via sum of squared deviations (Decimal).

    Uses Decimal.sqrt for exact intermediate; returns quantized Decimal.
    """
    if len(values) <= ddof:
        raise InvalidInputError(f"values는 {ddof + 1}개 이상 필요합니다.")
    sq = sum(((v - mean) ** 2 for v in values), Decimal("0"))
    var = sq / Decimal(len(values) - ddof)
    return var.sqrt()


def _quantile_sorted(sorted_values: list[Decimal], q: Decimal) -> Decimal:
    """Linear interpolation quantile (numpy default method)."""
    n = len(sorted_values)
    if n == 0:
        raise InvalidInputError("values가 비어있습니다.")
    if n == 1:
        return sorted_values[0]
    pos = q * Decimal(n - 1)
    lo  = int(pos)
    hi  = min(lo + 1, n - 1)
    frac = pos - Decimal(lo)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def _q8(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.00000001"))


@REGISTRY.tool(
    namespace="finance",
    name="var_historical",
    description=(
        "Historical VaR: 수익률 배열의 (1-confidence) 분위수를 손실로 반환. "
        "분포 가정 없음."
    ),
    version="1.0.0",
)
def finance_var_historical(
    returns:    list[str],
    confidence: str = "0.95",
) -> dict[str, Any]:
    """Historical Value at Risk.

    VaR = -quantile(returns, 1-confidence)
    CVaR(ES) = -mean(returns <= -VaR)

    Returns:
        {var, cvar, n, confidence, trace}
    """
    trace = CalcTrace(
        tool="finance.var_historical",
        formula="VaR = -empirical_quantile(returns, 1-c); CVaR = -mean(tail)",
    )
    conf = D(confidence)
    if not (Decimal("0") < conf < Decimal("1")):
        raise InvalidInputError("confidence는 (0, 1) 범위여야 합니다.")

    arr = _to_decimal_array(returns)
    if len(arr) < 2:
        raise InvalidInputError("returns는 2개 이상 필요합니다.")

    sorted_arr = sorted(arr)
    alpha = Decimal("1") - conf
    q_val = _quantile_sorted(sorted_arr, alpha)
    var   = -q_val

    # CVaR: mean of returns <= q_val
    tail = [v for v in sorted_arr if v <= q_val]
    if tail:
        cvar = -_mean_decimal(tail)
    else:
        cvar = var

    trace.input("returns_n",  len(arr))
    trace.input("confidence", confidence)
    trace.output({"var": str(_q8(var)), "cvar": str(_q8(cvar))})

    return {
        "var":        str(_q8(var)),
        "cvar":       str(_q8(cvar)),
        "n":          len(arr),
        "confidence": str(conf),
        "trace":      trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="var_parametric",
    description=(
        "Parametric VaR (정규분포 가정): VaR = -(mu + z_alpha * sigma). "
        "분포 모수 추정."
    ),
    version="1.0.0",
)
def finance_var_parametric(
    returns:    list[str],
    confidence: str = "0.95",
) -> dict[str, Any]:
    """Parametric (Gaussian) VaR.

    VaR = -(mu + z_{1-c} * sigma)  where z is standard normal ppf.
    CVaR = -(mu - sigma * phi(z) / (1-c))  (Closed-form Gaussian ES)
    """
    trace = CalcTrace(
        tool="finance.var_parametric",
        formula="VaR = -(mu + z*sigma); CVaR = -(mu - sigma*phi(z)/(1-c))",
    )
    conf = D(confidence)
    if not (Decimal("0") < conf < Decimal("1")):
        raise InvalidInputError("confidence는 (0, 1) 범위여야 합니다.")

    arr = _to_decimal_array(returns)
    if len(arr) < 2:
        raise InvalidInputError("returns는 2개 이상 필요합니다.")

    mu     = _mean_decimal(arr)
    sigma  = _stdev_decimal(arr, mu, ddof=1)
    alpha  = Decimal("1") - conf

    # z value via scipy (float OK — confidence level is not user data)
    z      = float(stats.norm.ppf(float(alpha)))
    z_d    = D(str(z))
    var    = -(mu + z_d * sigma)

    # CVaR Gaussian: -(mu - sigma * phi(z)/(1-c))
    phi_z  = float(stats.norm.pdf(z))
    tail_mean_adj = D(str(phi_z)) / alpha
    cvar   = -(mu - sigma * tail_mean_adj)

    trace.input("returns_n",  len(arr))
    trace.input("confidence", confidence)
    trace.step("mu",    str(_q8(mu)))
    trace.step("sigma", str(_q8(sigma)))
    trace.step("z",     str(_q8(z_d)))
    trace.output({"var": str(_q8(var)), "cvar": str(_q8(cvar))})

    return {
        "var":        str(_q8(var)),
        "cvar":       str(_q8(cvar)),
        "mu":         str(_q8(mu)),
        "sigma":      str(_q8(sigma)),
        "z":          str(_q8(z_d)),
        "n":          len(arr),
        "confidence": str(conf),
        "trace":      trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="sharpe_ratio",
    description=(
        "Sharpe ratio: (평균수익 - 무위험수익) / 표준편차. 연환산 옵션."
    ),
    version="1.0.0",
)
def finance_sharpe_ratio(
    returns:        list[str],
    risk_free_rate: str  = "0",
    periods_per_year: int = 0,
) -> dict[str, Any]:
    """Sharpe ratio.

    Args:
        returns:          기간별 수익률 배열
        risk_free_rate:   동일 기간 무위험 수익률 (기본 0)
        periods_per_year: 연환산 multiplier (예: 252 일간). 0이면 미환산.

    Returns:
        {sharpe, mean_excess, stdev, annualized, trace}
    """
    trace = CalcTrace(
        tool="finance.sharpe_ratio",
        formula="SR = (mean(r) - rf) / stdev(r); annualized = SR * sqrt(ppy)",
    )
    arr = _to_decimal_array(returns)
    rf  = D(risk_free_rate)
    if len(arr) < 2:
        raise InvalidInputError("returns는 2개 이상 필요합니다.")
    if periods_per_year < 0:
        raise InvalidInputError("periods_per_year는 0 이상이어야 합니다.")

    mu    = _mean_decimal(arr)
    sigma = _stdev_decimal(arr, mu, ddof=1)
    if sigma == Decimal("0"):
        raise InvalidInputError("표준편차가 0이어서 Sharpe ratio 계산 불가.")

    excess = mu - rf
    sharpe = excess / sigma

    annualized = (
        str(_q8(sharpe * Decimal(periods_per_year).sqrt()))
        if periods_per_year > 0 else None
    )

    trace.input("returns_n",        len(arr))
    trace.input("risk_free_rate",   risk_free_rate)
    trace.input("periods_per_year", periods_per_year)
    trace.output({"sharpe": str(_q8(sharpe))})

    return {
        "sharpe":       str(_q8(sharpe)),
        "mean_excess":  str(_q8(excess)),
        "stdev":        str(_q8(sigma)),
        "annualized":   annualized,
        "n":            len(arr),
        "trace":        trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="sortino_ratio",
    description=(
        "Sortino ratio: 하방편차만 사용한 위험조정수익률. "
        "Sharpe 대비 상승 변동성 페널티 제외."
    ),
    version="1.0.0",
)
def finance_sortino_ratio(
    returns:          list[str],
    risk_free_rate:   str  = "0",
    periods_per_year: int  = 0,
) -> dict[str, Any]:
    """Sortino ratio with downside semi-deviation.

    downside_dev = sqrt( mean( min(r - rf, 0)^2 ) )
    Sortino = (mean(r) - rf) / downside_dev
    """
    trace = CalcTrace(
        tool="finance.sortino_ratio",
        formula="Sortino = (mean(r) - rf) / sqrt(mean(min(r-rf,0)^2))",
    )
    arr = _to_decimal_array(returns)
    rf  = D(risk_free_rate)
    if len(arr) < 2:
        raise InvalidInputError("returns는 2개 이상 필요합니다.")
    if periods_per_year < 0:
        raise InvalidInputError("periods_per_year는 0 이상이어야 합니다.")

    mu      = _mean_decimal(arr)
    excess  = mu - rf

    downs = [min(r - rf, Decimal("0")) ** 2 for r in arr]
    down_mean = sum(downs, Decimal("0")) / Decimal(len(arr))
    down_dev  = down_mean.sqrt()

    if down_dev == Decimal("0"):
        raise InvalidInputError("하방편차가 0이어서 Sortino ratio 계산 불가.")

    sortino = excess / down_dev

    annualized = (
        str(_q8(sortino * Decimal(periods_per_year).sqrt()))
        if periods_per_year > 0 else None
    )

    trace.input("returns_n",        len(arr))
    trace.input("risk_free_rate",   risk_free_rate)
    trace.input("periods_per_year", periods_per_year)
    trace.output({"sortino": str(_q8(sortino))})

    return {
        "sortino":         str(_q8(sortino)),
        "mean_excess":     str(_q8(excess)),
        "downside_dev":    str(_q8(down_dev)),
        "annualized":      annualized,
        "n":               len(arr),
        "trace":           trace.to_dict(),
    }


__all__ = [
    "finance_var_historical",
    "finance_var_parametric",
    "finance_sharpe_ratio",
    "finance_sortino_ratio",
]


# numpy import kept for potential future parametric routines (unused at runtime).
_ = np
