"""Discrete distribution tools: binomial and poisson.
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
    _parse_prob,
    _validate_non_negative_int,
    stats,
)


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
