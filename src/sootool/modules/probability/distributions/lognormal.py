"""Lognormal distribution tools: pdf, cdf, ppf.
"""
from __future__ import annotations

from typing import Any

from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    _dist_result,
    _parse_float,
    _parse_quantile,
    _validate_positive_float,
    stats,
)


@REGISTRY.tool(
    namespace="probability",
    name="lognormal_pdf",
    description="로그정규분포 PDF: f(x; μ, σ). x>0, 원 분포 평균 μ, 표준편차 σ.",
    version="1.0.0",
)
def lognormal_pdf(x: str, mu: str = "0", sigma: str = "1") -> dict[str, Any]:
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
    description="로그정규분포 CDF = Φ((ln x - μ)/σ). x 는 양수, mu 와 sigma 는 ln x 의 평균과 표준편차(기본 0, 1).",
    version="1.0.0",
)
def lognormal_cdf(x: str, mu: str = "0", sigma: str = "1") -> dict[str, Any]:
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
    description="로그정규분포 역CDF. exp(μ + σ Φ⁻¹(q)).",
    version="1.0.0",
)
def lognormal_ppf(q: str, mu: str = "0", sigma: str = "1") -> dict[str, Any]:
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
