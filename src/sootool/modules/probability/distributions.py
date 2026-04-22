"""Probability distribution tools: normal, binomial, Poisson.

내부 자료형 (ADR-008):
- scipy.stats 내부 float64 사용.
- 입력: Decimal 문자열 → float64 변환 (cast.decimal_to_float64).
- 출력: float64 → cast.float64_to_decimal_str (10 significant digits).

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
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
