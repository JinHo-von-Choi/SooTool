"""Gamma family tools: gamma, exponential, chi-square.
"""
from __future__ import annotations

from typing import Any

from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    _dist_result,
    _parse_float,
    _parse_quantile,
    _validate_nonneg_float,
    _validate_positive_float,
    stats,
)


@REGISTRY.tool(
    namespace="probability",
    name="gamma_pdf",
    description="감마분포 PDF: f(x; k, θ). scipy.stats.gamma.pdf (k=shape, θ=scale).",
    version="1.0.0",
)
def gamma_pdf(x: str, shape: str, scale: str = "1") -> dict[str, Any]:
    x_f     = _parse_float(x,     "x")
    shape_f = _parse_float(shape, "shape")
    scale_f = _parse_float(scale, "scale")
    _validate_nonneg_float(x_f,        "x",     x)
    _validate_positive_float(shape_f,  "shape", shape)
    _validate_positive_float(scale_f,  "scale", scale)
    val = float(stats.gamma.pdf(x_f, a=shape_f, scale=scale_f))
    return _dist_result(
        "probability.gamma_pdf",
        "f(x; k, θ) = x^(k-1) * exp(-x/θ) / (Γ(k) * θ^k)",
        "pdf",
        {"x": x, "shape": shape, "scale": scale},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="gamma_cdf",
    description="감마분포 CDF: P(X ≤ x). scipy.stats.gamma.cdf.",
    version="1.0.0",
)
def gamma_cdf(x: str, shape: str, scale: str = "1") -> dict[str, Any]:
    x_f     = _parse_float(x,     "x")
    shape_f = _parse_float(shape, "shape")
    scale_f = _parse_float(scale, "scale")
    _validate_nonneg_float(x_f,        "x",     x)
    _validate_positive_float(shape_f,  "shape", shape)
    _validate_positive_float(scale_f,  "scale", scale)
    val = float(stats.gamma.cdf(x_f, a=shape_f, scale=scale_f))
    return _dist_result(
        "probability.gamma_cdf",
        "P(X ≤ x) = γ(k, x/θ) / Γ(k)",
        "cdf",
        {"x": x, "shape": shape, "scale": scale},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="gamma_ppf",
    description="감마분포 역CDF: x = F⁻¹(q). scipy.stats.gamma.ppf.",
    version="1.0.0",
)
def gamma_ppf(q: str, shape: str, scale: str = "1") -> dict[str, Any]:
    q_f     = _parse_quantile(q,  "q")
    shape_f = _parse_float(shape, "shape")
    scale_f = _parse_float(scale, "scale")
    _validate_positive_float(shape_f, "shape", shape)
    _validate_positive_float(scale_f, "scale", scale)
    val = float(stats.gamma.ppf(q_f, a=shape_f, scale=scale_f))
    return _dist_result(
        "probability.gamma_ppf",
        "x = F⁻¹(q; k, θ)",
        "ppf",
        {"q": q, "shape": shape, "scale": scale},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="exponential_pdf",
    description="지수분포 PDF: f(x; λ) = λ e^(-λx). scale=1/λ 사용.",
    version="1.0.0",
)
def exponential_pdf(x: str, rate: str) -> dict[str, Any]:
    x_f    = _parse_float(x,    "x")
    rate_f = _parse_float(rate, "rate")
    _validate_nonneg_float(x_f,        "x",    x)
    _validate_positive_float(rate_f,   "rate", rate)
    val = float(stats.expon.pdf(x_f, scale=1.0 / rate_f))
    return _dist_result(
        "probability.exponential_pdf",
        "f(x; λ) = λ * exp(-λ x)",
        "pdf",
        {"x": x, "rate": rate},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="exponential_cdf",
    description="지수분포 CDF: P(X ≤ x) = 1 - e^(-λx).",
    version="1.0.0",
)
def exponential_cdf(x: str, rate: str) -> dict[str, Any]:
    x_f    = _parse_float(x,    "x")
    rate_f = _parse_float(rate, "rate")
    _validate_nonneg_float(x_f,        "x",    x)
    _validate_positive_float(rate_f,   "rate", rate)
    val = float(stats.expon.cdf(x_f, scale=1.0 / rate_f))
    return _dist_result(
        "probability.exponential_cdf",
        "P(X ≤ x) = 1 - exp(-λ x)",
        "cdf",
        {"x": x, "rate": rate},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="exponential_ppf",
    description="지수분포 역CDF(분위수) x = -ln(1-q)/λ. q 는 0 이상 1 미만의 확률, rate 는 λ.",
    version="1.0.0",
)
def exponential_ppf(q: str, rate: str) -> dict[str, Any]:
    q_f    = _parse_quantile(q, "q")
    rate_f = _parse_float(rate, "rate")
    _validate_positive_float(rate_f, "rate", rate)
    val = float(stats.expon.ppf(q_f, scale=1.0 / rate_f))
    return _dist_result(
        "probability.exponential_ppf",
        "x = -ln(1 - q) / λ",
        "ppf",
        {"q": q, "rate": rate},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="chi_square_pdf",
    description="카이제곱분포 PDF. scipy.stats.chi2.pdf, df = 자유도.",
    version="1.0.0",
)
def chi_square_pdf(x: str, df: str) -> dict[str, Any]:
    x_f  = _parse_float(x,  "x")
    df_f = _parse_float(df, "df")
    _validate_nonneg_float(x_f,        "x",  x)
    _validate_positive_float(df_f,     "df", df)
    val = float(stats.chi2.pdf(x_f, df=df_f))
    return _dist_result(
        "probability.chi_square_pdf",
        "f(x; k) = x^(k/2-1) e^(-x/2) / (2^(k/2) Γ(k/2))",
        "pdf",
        {"x": x, "df": df},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="chi_square_cdf",
    description="카이제곱분포 CDF. scipy.stats.chi2.cdf.",
    version="1.0.0",
)
def chi_square_cdf(x: str, df: str) -> dict[str, Any]:
    x_f  = _parse_float(x,  "x")
    df_f = _parse_float(df, "df")
    _validate_nonneg_float(x_f,        "x",  x)
    _validate_positive_float(df_f,     "df", df)
    val = float(stats.chi2.cdf(x_f, df=df_f))
    return _dist_result(
        "probability.chi_square_cdf",
        "P(X ≤ x) = P(k/2, x/2)",
        "cdf",
        {"x": x, "df": df},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="chi_square_ppf",
    description="카이제곱분포 역CDF(분위수). q 는 0~1 사이 확률, df 는 자유도.",
    version="1.0.0",
)
def chi_square_ppf(q: str, df: str) -> dict[str, Any]:
    q_f  = _parse_quantile(q,  "q")
    df_f = _parse_float(df,    "df")
    _validate_positive_float(df_f, "df", df)
    val = float(stats.chi2.ppf(q_f, df=df_f))
    return _dist_result(
        "probability.chi_square_ppf",
        "x = P⁻¹(k/2, q) * 2",
        "ppf",
        {"q": q, "df": df},
        val,
    )
