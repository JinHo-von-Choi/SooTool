"""Probability distribution tools: normal, binomial, Poisson.

내부 자료형 (ADR-008):
- scipy.stats 내부 float64 사용.
- 입력: Decimal 문자열 → float64 변환 (cast.decimal_to_float64).
- 출력: float64 → cast.float64_to_decimal_str (10 significant digits).

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from typing import Any

from scipy import stats

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_SIG_DIGITS = 10  # significant digits for output


def _parse_float(value: str, name: str) -> float:
    try:
        return decimal_to_float64(D(value))
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


def _parse_prob(value: str, name: str) -> float:
    p = _parse_float(value, name)
    if p < 0.0 or p > 1.0:
        raise DomainConstraintError(f"{name}={value}은(는) [0, 1] 범위를 벗어납니다.")
    return p


def _parse_quantile(value: str, name: str) -> float:
    q = _parse_float(value, name)
    if q <= 0.0 or q >= 1.0:
        raise DomainConstraintError(f"{name}={value}은(는) (0, 1) 열린 구간이어야 합니다.")
    return q


def _validate_non_negative_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f"{name}은(는) 정수여야 합니다: {value!r}")
    if value < 0:
        raise DomainConstraintError(f"{name}은(는) 음수가 될 수 없습니다: {value}")


# ---------------------------------------------------------------------------
# Normal distribution
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Binomial distribution
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="probability",
    name="binomial_pmf",
    description="이항분포 PMF: P(X=k; n, p). scipy.stats.binom.pmf.",
    version="1.0.0",
)
def binomial_pmf(k: int, n: int, p: str) -> dict[str, Any]:
    """Compute the binomial distribution PMF: P(X = k).

    Args:
        k: Number of successes (non-negative integer, k <= n).
        n: Number of trials (non-negative integer).
        p: Success probability (Decimal string in [0, 1]).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.binomial_pmf",
        formula="P(X=k) = C(n,k) * p^k * (1-p)^(n-k)",
    )
    _validate_non_negative_int(k, "k")
    _validate_non_negative_int(n, "n")
    p_f = _parse_prob(p, "p")

    if k > n:
        raise DomainConstraintError(f"k({k})은(는) n({n})을 초과할 수 없습니다.")

    trace.input("k", k)
    trace.input("n", n)
    trace.input("p", p)

    result_f   = float(stats.binom.pmf(k, n, p_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("pmf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="probability",
    name="binomial_cdf",
    description="이항분포 CDF: P(X≤k; n, p). scipy.stats.binom.cdf.",
    version="1.0.0",
)
def binomial_cdf(k: int, n: int, p: str) -> dict[str, Any]:
    """Compute the binomial distribution CDF: P(X <= k).

    Args:
        k: Upper bound for successes (non-negative integer, k <= n).
        n: Number of trials (non-negative integer).
        p: Success probability (Decimal string in [0, 1]).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.binomial_cdf",
        formula="P(X≤k) = Σ_{i=0}^{k} C(n,i) * p^i * (1-p)^(n-i)",
    )
    _validate_non_negative_int(k, "k")
    _validate_non_negative_int(n, "n")
    p_f = _parse_prob(p, "p")

    if k > n:
        raise DomainConstraintError(f"k({k})은(는) n({n})을 초과할 수 없습니다.")

    trace.input("k", k)
    trace.input("n", n)
    trace.input("p", p)

    result_f   = float(stats.binom.cdf(k, n, p_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("cdf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Poisson distribution
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="probability",
    name="poisson_pmf",
    description="포아송 분포 PMF: P(X=k; λ). scipy.stats.poisson.pmf.",
    version="1.0.0",
)
def poisson_pmf(k: int, lam: str) -> dict[str, Any]:
    """Compute the Poisson distribution PMF: P(X = k).

    Args:
        k:   Number of events (non-negative integer).
        lam: Rate parameter λ > 0 (Decimal string).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.poisson_pmf",
        formula="P(X=k) = (λ^k * e^-λ) / k!",
    )
    _validate_non_negative_int(k, "k")
    lam_f = _parse_float(lam, "lam")

    if lam_f <= 0.0:
        raise DomainConstraintError(f"lam(λ)은 양수여야 합니다: {lam}")

    trace.input("k",   k)
    trace.input("lam", lam)

    result_f   = float(stats.poisson.pmf(k, lam_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("pmf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="probability",
    name="poisson_cdf",
    description="포아송 분포 CDF: P(X≤k; λ). scipy.stats.poisson.cdf.",
    version="1.0.0",
)
def poisson_cdf(k: int, lam: str) -> dict[str, Any]:
    """Compute the Poisson distribution CDF: P(X <= k).

    Args:
        k:   Upper bound (non-negative integer).
        lam: Rate parameter λ > 0 (Decimal string).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="probability.poisson_cdf",
        formula="P(X≤k) = Σ_{i=0}^{k} (λ^i * e^-λ) / i!",
    )
    _validate_non_negative_int(k, "k")
    lam_f = _parse_float(lam, "lam")

    if lam_f <= 0.0:
        raise DomainConstraintError(f"lam(λ)은 양수여야 합니다: {lam}")

    trace.input("k",   k)
    trace.input("lam", lam)

    result_f   = float(stats.poisson.cdf(k, lam_f))
    result_str = float64_to_decimal_str(result_f, digits=_SIG_DIGITS)

    trace.step("cdf", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Gamma distribution  (shape=k, scale=θ)
# ---------------------------------------------------------------------------

def _validate_positive_float(value: float, name: str, raw: str) -> None:
    if value <= 0.0:
        raise DomainConstraintError(f"{name}은(는) 양수여야 합니다: {raw}")


def _validate_nonneg_float(value: float, name: str, raw: str) -> None:
    if value < 0.0:
        raise DomainConstraintError(f"{name}은(는) 음수가 될 수 없습니다: {raw}")


def _dist_result(
    tool_name: str,
    formula: str,
    label: str,
    inputs: dict[str, Any],
    value: float,
) -> dict[str, Any]:
    trace = CalcTrace(tool=tool_name, formula=formula)
    for k_, v_ in inputs.items():
        trace.input(k_, v_)
    result_str = float64_to_decimal_str(value, digits=_SIG_DIGITS)
    trace.step(label, result_str)
    trace.output({"result": result_str})
    return {"result": result_str, "trace": trace.to_dict()}


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


# ---------------------------------------------------------------------------
# Beta distribution  (α, β on [0, 1])
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="probability",
    name="beta_pdf",
    description="베타분포 PDF: f(x; α, β). scipy.stats.beta.pdf, 지지역 [0, 1].",
    version="1.0.0",
)
def beta_pdf(x: str, alpha: str, beta: str) -> dict[str, Any]:
    x_f     = _parse_float(x,     "x")
    alpha_f = _parse_float(alpha, "alpha")
    beta_f  = _parse_float(beta,  "beta")
    if x_f < 0.0 or x_f > 1.0:
        raise DomainConstraintError(f"x={x}은(는) [0, 1] 구간이어야 합니다.")
    _validate_positive_float(alpha_f, "alpha", alpha)
    _validate_positive_float(beta_f,  "beta",  beta)
    val = float(stats.beta.pdf(x_f, a=alpha_f, b=beta_f))
    return _dist_result(
        "probability.beta_pdf",
        "f(x; α, β) = x^(α-1) * (1-x)^(β-1) / B(α, β)",
        "pdf",
        {"x": x, "alpha": alpha, "beta": beta},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="beta_cdf",
    description="베타분포 CDF: P(X ≤ x). scipy.stats.beta.cdf, 정규화 불완전 베타함수.",
    version="1.0.0",
)
def beta_cdf(x: str, alpha: str, beta: str) -> dict[str, Any]:
    x_f     = _parse_float(x,     "x")
    alpha_f = _parse_float(alpha, "alpha")
    beta_f  = _parse_float(beta,  "beta")
    if x_f < 0.0 or x_f > 1.0:
        raise DomainConstraintError(f"x={x}은(는) [0, 1] 구간이어야 합니다.")
    _validate_positive_float(alpha_f, "alpha", alpha)
    _validate_positive_float(beta_f,  "beta",  beta)
    val = float(stats.beta.cdf(x_f, a=alpha_f, b=beta_f))
    return _dist_result(
        "probability.beta_cdf",
        "P(X ≤ x) = I_x(α, β)",
        "cdf",
        {"x": x, "alpha": alpha, "beta": beta},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="beta_ppf",
    description="베타분포 역CDF. scipy.stats.beta.ppf.",
    version="1.0.0",
)
def beta_ppf(q: str, alpha: str, beta: str) -> dict[str, Any]:
    q_f     = _parse_quantile(q,  "q")
    alpha_f = _parse_float(alpha, "alpha")
    beta_f  = _parse_float(beta,  "beta")
    _validate_positive_float(alpha_f, "alpha", alpha)
    _validate_positive_float(beta_f,  "beta",  beta)
    val = float(stats.beta.ppf(q_f, a=alpha_f, b=beta_f))
    return _dist_result(
        "probability.beta_ppf",
        "x = I⁻¹_q(α, β)",
        "ppf",
        {"q": q, "alpha": alpha, "beta": beta},
        val,
    )


# ---------------------------------------------------------------------------
# Exponential distribution  (rate λ > 0)
# ---------------------------------------------------------------------------

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
    description="지수분포 역CDF: x = -ln(1-q)/λ.",
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


# ---------------------------------------------------------------------------
# Log-normal distribution  (mu, sigma of the underlying normal ln X)
# ---------------------------------------------------------------------------

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
    description="로그정규분포 CDF. Φ((ln x - μ)/σ).",
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


# ---------------------------------------------------------------------------
# Chi-square distribution  (df > 0)
# ---------------------------------------------------------------------------

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
    description="카이제곱분포 역CDF.",
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


# ---------------------------------------------------------------------------
# F distribution  (dfn, dfd > 0)
# ---------------------------------------------------------------------------

@REGISTRY.tool(
    namespace="probability",
    name="f_pdf",
    description="F 분포 PDF. scipy.stats.f.pdf, dfn/dfd 분자·분모 자유도.",
    version="1.0.0",
)
def f_pdf(x: str, dfn: str, dfd: str) -> dict[str, Any]:
    x_f   = _parse_float(x,   "x")
    dfn_f = _parse_float(dfn, "dfn")
    dfd_f = _parse_float(dfd, "dfd")
    _validate_nonneg_float(x_f,        "x",   x)
    _validate_positive_float(dfn_f,    "dfn", dfn)
    _validate_positive_float(dfd_f,    "dfd", dfd)
    val = float(stats.f.pdf(x_f, dfn=dfn_f, dfd=dfd_f))
    return _dist_result(
        "probability.f_pdf",
        "f(x; d1, d2) = √((d1 x)^d1 d2^d2 / ((d1 x + d2)^(d1+d2))) / (x B(d1/2, d2/2))",
        "pdf",
        {"x": x, "dfn": dfn, "dfd": dfd},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="f_cdf",
    description="F 분포 CDF. scipy.stats.f.cdf.",
    version="1.0.0",
)
def f_cdf(x: str, dfn: str, dfd: str) -> dict[str, Any]:
    x_f   = _parse_float(x,   "x")
    dfn_f = _parse_float(dfn, "dfn")
    dfd_f = _parse_float(dfd, "dfd")
    _validate_nonneg_float(x_f,        "x",   x)
    _validate_positive_float(dfn_f,    "dfn", dfn)
    _validate_positive_float(dfd_f,    "dfd", dfd)
    val = float(stats.f.cdf(x_f, dfn=dfn_f, dfd=dfd_f))
    return _dist_result(
        "probability.f_cdf",
        "P(X ≤ x) = I_{d1 x/(d1 x + d2)}(d1/2, d2/2)",
        "cdf",
        {"x": x, "dfn": dfn, "dfd": dfd},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="f_ppf",
    description="F 분포 역CDF.",
    version="1.0.0",
)
def f_ppf(q: str, dfn: str, dfd: str) -> dict[str, Any]:
    q_f   = _parse_quantile(q, "q")
    dfn_f = _parse_float(dfn,  "dfn")
    dfd_f = _parse_float(dfd,  "dfd")
    _validate_positive_float(dfn_f,    "dfn", dfn)
    _validate_positive_float(dfd_f,    "dfd", dfd)
    val = float(stats.f.ppf(q_f, dfn=dfn_f, dfd=dfd_f))
    return _dist_result(
        "probability.f_ppf",
        "x = F⁻¹(q; d1, d2)",
        "ppf",
        {"q": q, "dfn": dfn, "dfd": dfd},
        val,
    )
