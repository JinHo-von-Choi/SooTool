"""Lognormal distribution tools: pdf, cdf, ppf.
"""
from __future__ import annotations

from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    DistributionResult,
    _dist_result,
    _parse_float,
    _parse_quantile,
    _validate_positive_float,
    stats,
)


@REGISTRY.tool(
    namespace="probability",
    name="lognormal_pdf",
    description="로그정규분포의 확률밀도를 구한다. x 는 양수, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. mu 와 sigma 는 X 자체의 평균과 표준편차가 아니다.",
    version="1.0.0",
)
def lognormal_pdf(x: str, mu: str = "0", sigma: str = "1") -> DistributionResult:
    x_f     = _parse_float(x,     "x")
    mu_f    = _parse_float(mu,    "mu")
    sigma_f = _parse_float(sigma, "sigma")
    if x_f <= 0.0:
        raise DomainConstraintError(f"x는 양수여야 합니다: {x}")
    _validate_positive_float(sigma_f, "sigma", sigma)
    import math as _math  # noqa: PLC0415
    val = float(stats.lognorm.pdf(x_f, s=sigma_f, scale=_math.exp(mu_f)))
    return _dist_result(
        "probability.lognormal_pdf",
        "f(x) = 1/(x σ √(2π)) * exp(-((ln x - μ)² / (2σ²)))",
        "pdf",
        {"x": x, "mu": mu, "sigma": sigma},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="lognormal_cdf",
    description="로그정규분포의 누적확률 P(X ≤ x) = Φ((ln x - μ)/σ)를 구한다. x 는 양수, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. mu 와 sigma 에 X 자체의 통계량을 넣으면 틀린다.",
    version="1.0.0",
)
def lognormal_cdf(x: str, mu: str = "0", sigma: str = "1") -> DistributionResult:
    x_f     = _parse_float(x,     "x")
    mu_f    = _parse_float(mu,    "mu")
    sigma_f = _parse_float(sigma, "sigma")
    if x_f <= 0.0:
        raise DomainConstraintError(f"x는 양수여야 합니다: {x}")
    _validate_positive_float(sigma_f, "sigma", sigma)
    import math as _math  # noqa: PLC0415
    val = float(stats.lognorm.cdf(x_f, s=sigma_f, scale=_math.exp(mu_f)))
    return _dist_result(
        "probability.lognormal_cdf",
        "P(X ≤ x) = Φ((ln x - μ) / σ)",
        "cdf",
        {"x": x, "mu": mu, "sigma": sigma},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="lognormal_ppf",
    description="로그정규분포의 분위수 exp(μ + σΦ⁻¹(q))를 구한다. q 는 0 초과 1 미만, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. mu 와 sigma 에 X 자체의 통계량을 넣으면 틀린다.",
    version="1.0.0",
)
def lognormal_ppf(q: str, mu: str = "0", sigma: str = "1") -> DistributionResult:
    q_f     = _parse_quantile(q,  "q")
    mu_f    = _parse_float(mu,    "mu")
    sigma_f = _parse_float(sigma, "sigma")
    _validate_positive_float(sigma_f, "sigma", sigma)
    import math as _math  # noqa: PLC0415
    val = float(stats.lognorm.ppf(q_f, s=sigma_f, scale=_math.exp(mu_f)))
    return _dist_result(
        "probability.lognormal_ppf",
        "x = exp(μ + σ Φ⁻¹(q))",
        "ppf",
        {"q": q, "mu": mu, "sigma": sigma},
        val,
    )
