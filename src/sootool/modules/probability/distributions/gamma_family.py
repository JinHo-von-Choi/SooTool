"""Gamma family tools: gamma, exponential, chi-square.
"""
from __future__ import annotations

from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    DistributionResult,
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
    description="감마분포의 확률밀도 f(x; k, θ)를 구한다. x 는 0 이상, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. scale 은 rate 의 역수이므로 rate 를 그대로 넣으면 틀린다.",
    version="1.0.0",
)
def gamma_pdf(x: str, shape: str, scale: str = "1") -> DistributionResult:
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
    description="감마분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. scale 은 rate 의 역수이므로 rate 를 그대로 넣으면 틀린다.",
    version="1.0.0",
)
def gamma_cdf(x: str, shape: str, scale: str = "1") -> DistributionResult:
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
    description="감마분포의 분위수를 구한다. q 는 0 초과 1 미만, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. scale 은 rate 의 역수이므로 rate 를 그대로 넣으면 틀린다.",
    version="1.0.0",
)
def gamma_ppf(q: str, shape: str, scale: str = "1") -> DistributionResult:
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
    description="지수분포의 확률밀도 f(x; λ) = λe^(-λx)를 구한다. x 는 0 이상, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. rate 에 평균(1/λ)을 넣으면 틀린다.",
    version="1.0.0",
)
def exponential_pdf(x: str, rate: str) -> DistributionResult:
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
    description="지수분포의 누적확률 P(X ≤ x) = 1 - e^(-λx)를 구한다. x 는 0 이상, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. rate 에 평균(1/λ)을 넣으면 틀린다.",
    version="1.0.0",
)
def exponential_cdf(x: str, rate: str) -> DistributionResult:
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
    description="지수분포의 분위수 x = -ln(1-q)/λ 를 구한다. q 는 0 초과 1 미만, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. rate 에 평균(1/λ)을 넣으면 틀린다.",
    version="1.0.0",
)
def exponential_ppf(q: str, rate: str) -> DistributionResult:
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
    description="카이제곱분포의 확률밀도를 구한다. x 는 0 이상, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 밀도값이지 확률이 아니므로 누적확률은 chi_square_cdf 를 쓴다.",
    version="1.0.0",
)
def chi_square_pdf(x: str, df: str) -> DistributionResult:
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
    description="카이제곱분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 검정의 p 값은 1 에서 이 값을 뺀 오른쪽 꼬리다.",
    version="1.0.0",
)
def chi_square_cdf(x: str, df: str) -> DistributionResult:
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
    description="카이제곱분포의 분위수를 구한다. q 는 0 초과 1 미만, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 유의수준 α 의 임계값은 q 에 1-α 를 넣는다.",
    version="1.0.0",
)
def chi_square_ppf(q: str, df: str) -> DistributionResult:
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
