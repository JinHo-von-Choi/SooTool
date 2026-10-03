"""Normal distribution tools: pdf, cdf, ppf.
"""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    _SIG_DIGITS,
    _parse_float,
    _parse_quantile,
    stats,
)


@REGISTRY.tool(
    namespace="probability",
    name="normal_pdf",
    description="정규분포 PDF: f(x; μ, σ). scipy.stats.norm.pdf, 10 유효 자리 출력.",
    version="1.0.0",
)
def normal_pdf(
    x: str,
    mu: str = "0",
    sigma: str = "1",
) -> dict[str, Any]:
    """Compute the normal distribution PDF value.

    Args:
        x:     Point at which to evaluate (Decimal string).
        mu:    Mean (Decimal string, default "0").
        sigma: Standard deviation (Decimal string, positive, default "1").

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.normal_pdf",
        formula="f(x; μ, σ) = (1/(σ√(2π))) * exp(-((x-μ)²/(2σ²)))",
    )
    x_f     = _parse_float(x,     "x")
    mu_f    = _parse_float(mu,    "mu")
    sigma_f = _parse_float(sigma, "sigma")

    if sigma_f <= 0.0:
        raise DomainConstraintError(f"sigma는 양수여야 합니다: {sigma}")

    trace.input("x",     x)
    trace.input("mu",    mu)
    trace.input("sigma", sigma)

    result_f   = float(stats.norm.pdf(x_f, loc=mu_f, scale=sigma_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("pdf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="probability",
    name="normal_cdf",
    description="정규분포 CDF: P(X ≤ x). scipy.stats.norm.cdf.",
    version="1.0.0",
)
def normal_cdf(
    x: str,
    mu: str = "0",
    sigma: str = "1",
) -> dict[str, Any]:
    """Compute the normal distribution CDF value P(X <= x).

    Args:
        x:     Point (Decimal string).
        mu:    Mean (Decimal string, default "0").
        sigma: Standard deviation (Decimal string, positive, default "1").

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.normal_cdf",
        formula="P(X ≤ x) = Φ((x-μ)/σ)",
    )
    x_f     = _parse_float(x,     "x")
    mu_f    = _parse_float(mu,    "mu")
    sigma_f = _parse_float(sigma, "sigma")

    if sigma_f <= 0.0:
        raise DomainConstraintError(f"sigma는 양수여야 합니다: {sigma}")

    trace.input("x",     x)
    trace.input("mu",    mu)
    trace.input("sigma", sigma)

    result_f   = float(stats.norm.cdf(x_f, loc=mu_f, scale=sigma_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("cdf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="probability",
    name="normal_ppf",
    description="정규분포 역CDF(분위수함수): x = Φ⁻¹(q). scipy.stats.norm.ppf.",
    version="1.0.0",
)
def normal_ppf(
    q: str,
    mu: str = "0",
    sigma: str = "1",
) -> dict[str, Any]:
    """Compute the normal distribution percent point function (inverse CDF).

    Args:
        q:     Quantile in (0, 1) (Decimal string).
        mu:    Mean (Decimal string, default "0").
        sigma: Standard deviation (Decimal string, positive, default "1").

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.normal_ppf",
        formula="x = μ + σ * Φ⁻¹(q)",
    )
    q_f     = _parse_quantile(q, "q")
    mu_f    = _parse_float(mu,    "mu")
    sigma_f = _parse_float(sigma, "sigma")

    if sigma_f <= 0.0:
        raise DomainConstraintError(f"sigma는 양수여야 합니다: {sigma}")

    trace.input("q",     q)
    trace.input("mu",    mu)
    trace.input("sigma", sigma)

    result_f   = float(stats.norm.ppf(q_f, loc=mu_f, scale=sigma_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("ppf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}
