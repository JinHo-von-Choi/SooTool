"""Normal distribution tools: pdf, cdf, ppf.
"""
from __future__ import annotations

from sootool.core.audit import CalcTrace
from sootool.core.cast import float64_to_decimal_str
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    _SIG_DIGITS,
    DistributionResult,
    _parse_float,
    _parse_quantile,
    stats,
)


@REGISTRY.tool(
    namespace="probability",
    name="normal_pdf",
    description="정규분포의 확률밀도 f(x; μ, σ)를 구한다. x, mu(평균, 기본 0), sigma(표준편차, 양수, 기본 1)는 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 밀도값이지 확률이 아니므로 구간 확률은 normal_cdf 의 차로 구한다.",
    version="1.0.0",
)
def normal_pdf(
    x: str,
    mu: str = "0",
    sigma: str = "1",
) -> DistributionResult:
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
    description="정규분포의 누적확률 P(X ≤ x)를 구한다. x, mu(평균, 기본 0), sigma(표준편차, 양수, 기본 1)는 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. sigma 에 분산을 넣으면 틀리므로 표준편차를 넣는다.",
    version="1.0.0",
)
def normal_cdf(
    x: str,
    mu: str = "0",
    sigma: str = "1",
) -> DistributionResult:
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
    description="정규분포의 분위수 x = μ + σΦ⁻¹(q)를 구한다. q 는 0 초과 1 미만 확률, mu(기본 0), sigma(표준편차, 양수, 기본 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. q 가 0 또는 1 이면 오류이고, 양측 임계값은 q 에 1-α/2 를 넣는다.",
    version="1.0.0",
)
def normal_ppf(
    q: str,
    mu: str = "0",
    sigma: str = "1",
) -> DistributionResult:
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
