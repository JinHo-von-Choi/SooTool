"""Finance option pricer: Black-Scholes European option model with Greeks.

공식 출처: Black, F. & Scholes, M. (1973). "The Pricing of Options and Corporate Liabilities."
          Journal of Political Economy, 81(3), 637-654.

  d1 = (ln(S/K) + (r - q + sigma^2/2) * T) / (sigma * sqrt(T))
  d2 = d1 - sigma * sqrt(T)
  call = S*exp(-q*T)*N(d1) - K*exp(-r*T)*N(d2)
  put  = K*exp(-r*T)*N(-d2) - S*exp(-q*T)*N(-d1)

Greeks (call):
  delta = exp(-q*T) * N(d1)
  gamma = exp(-q*T) * phi(d1) / (S * sigma * sqrt(T))
  vega  = S * exp(-q*T) * phi(d1) * sqrt(T)           [per unit sigma]
  theta = -(S*phi(d1)*sigma*exp(-q*T))/(2*sqrt(T))
          - r*K*exp(-r*T)*N(d2) + q*S*exp(-q*T)*N(d1) [per year]
  rho   = K*T*exp(-r*T)*N(d2)

Put Greeks differ by sign on delta, theta, rho per standard derivations.

자료형: mpmath internally (high-precision CDF), returned as Decimal strings via cast.mpmath_to_decimal.
       ADR-008: options use mpmath path.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath as mp

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

# Use 50 decimal digits of precision for mpmath computations
mp.mp.dps = 50


def _ncdf(x: mp.mpf) -> mp.mpf:
    """Standard normal CDF: N(x) = 0.5 * (1 + erf(x / sqrt(2)))."""
    return mp.mpf("0.5") * (1 + mp.erf(x / mp.sqrt(2)))


def _npdf(x: mp.mpf) -> mp.mpf:
    """Standard normal PDF: phi(x) = exp(-x^2/2) / sqrt(2*pi)."""
    return mp.exp(-x * x / 2) / mp.sqrt(2 * mp.pi)


def _to_mpf(s: str) -> mp.mpf:
    return mp.mpf(s)


@REGISTRY.tool(
    namespace="finance",
    name="black_scholes",
    description=(
        "Black-Scholes 유럽형 옵션 가격 및 Greeks 계산. "
        "mpmath 고정밀 정규분포 CDF 사용."
    ),
    version="1.0.0",
)
def black_scholes(
    spot: str,
    strike: str,
    time_to_expiry: str,
    rate: str,
    sigma: str,
    option_type: str,
    dividend_yield: str = "0",
) -> dict[str, Any]:
    """Compute Black-Scholes European option price and Greeks.

    Args:
        spot:           현재 주가 S (Decimal string)
        strike:         행사가 K (Decimal string)
        time_to_expiry: 만기까지 시간 T (년, Decimal string)
        rate:           무위험 이자율 r (Decimal string)
        sigma:          변동성 (Decimal string)
        option_type:    "call" | "put"
        dividend_yield: 배당 수익률 q (기본 "0")

    Returns:
        {price, delta, gamma, vega, theta, rho, trace}
        (all Decimal strings with ~6 significant decimals)
    """
    trace = CalcTrace(
        tool="finance.black_scholes",
        formula=(
            "d1=(ln(S/K)+(r-q+sigma^2/2)*T)/(sigma*sqrt(T)); "
            "d2=d1-sigma*sqrt(T); call=S*e^(-qT)*N(d1)-K*e^(-rT)*N(d2)"
        ),
    )

    option_type_lower = option_type.lower()
    if option_type_lower not in ("call", "put"):
        raise InvalidInputError(
            f"option_type은 'call' 또는 'put'이어야 합니다. 입력값: {option_type!r}"
        )

    if Decimal(spot) <= Decimal("0"):
        raise InvalidInputError("spot는 양수여야 합니다.")
    if Decimal(strike) <= Decimal("0"):
        raise InvalidInputError("strike는 양수여야 합니다.")
    if Decimal(time_to_expiry) <= Decimal("0"):
        raise InvalidInputError("time_to_expiry는 양수여야 합니다.")
    if Decimal(sigma) <= Decimal("0"):
        raise InvalidInputError("sigma는 양수여야 합니다.")
    if Decimal(dividend_yield) < Decimal("0"):
        raise InvalidInputError("dividend_yield는 0 이상이어야 합니다.")

    trace.input("spot",           spot)
    trace.input("strike",         strike)
    trace.input("time_to_expiry", time_to_expiry)
    trace.input("rate",           rate)
    trace.input("sigma",          sigma)
    trace.input("option_type",    option_type_lower)
    trace.input("dividend_yield", dividend_yield)

    # Convert to mpmath for high-precision computation
    S = _to_mpf(spot)
    K = _to_mpf(strike)
    T = _to_mpf(time_to_expiry)
    r = _to_mpf(rate)
    v = _to_mpf(sigma)           # sigma
    q = _to_mpf(dividend_yield)

    sqrt_T = mp.sqrt(T)

    d1 = (mp.log(S / K) + (r - q + v * v / 2) * T) / (v * sqrt_T)
    d2 = d1 - v * sqrt_T

    trace.step("d1", str(mpmath_to_decimal(d1, 10)))
    trace.step("d2", str(mpmath_to_decimal(d2, 10)))

    exp_neg_rT = mp.exp(-r * T)
    exp_neg_qT = mp.exp(-q * T)

    Nd1  = _ncdf(d1)
    Nd2  = _ncdf(d2)
    Nnd1 = _ncdf(-d1)
    Nnd2 = _ncdf(-d2)
    phid1 = _npdf(d1)

    if option_type_lower == "call":
        price_mp = S * exp_neg_qT * Nd1 - K * exp_neg_rT * Nd2
        delta_mp = exp_neg_qT * Nd1
        theta_mp = (
            -(S * phid1 * v * exp_neg_qT) / (2 * sqrt_T)
            - r * K * exp_neg_rT * Nd2
            + q * S * exp_neg_qT * Nd1
        )
        rho_mp = K * T * exp_neg_rT * Nd2
    else:  # put
        price_mp = K * exp_neg_rT * Nnd2 - S * exp_neg_qT * Nnd1
        delta_mp = exp_neg_qT * (Nd1 - 1)
        theta_mp = (
            -(S * phid1 * v * exp_neg_qT) / (2 * sqrt_T)
            + r * K * exp_neg_rT * Nnd2
            - q * S * exp_neg_qT * Nnd1
        )
        rho_mp = -K * T * exp_neg_rT * Nnd2

    # Gamma and Vega are identical for call and put
    gamma_mp = (exp_neg_qT * phid1) / (S * v * sqrt_T)
    vega_mp  = S * exp_neg_qT * phid1 * sqrt_T

    def _fmt(x: mp.mpf) -> str:
        return str(mpmath_to_decimal(x, 12))

    result = {
        "price": _fmt(price_mp),
        "delta": _fmt(delta_mp),
        "gamma": _fmt(gamma_mp),
        "vega":  _fmt(vega_mp),
        "theta": _fmt(theta_mp),
        "rho":   _fmt(rho_mp),
    }

    trace.step("price", result["price"])
    trace.step("delta", result["delta"])
    trace.step("gamma", result["gamma"])
    trace.step("vega",  result["vega"])
    trace.step("theta", result["theta"])
    trace.step("rho",   result["rho"])
    trace.output(result)

    return {**result, "trace": trace.to_dict()}
