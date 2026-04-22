"""Finance bond tools: YTM and Duration.

공식 출처: Fabozzi, "Fixed Income Mathematics", 4th ed.
  YTM: solve P = sum(C/(1+y/f)^t) + F/(1+y/f)^n via Newton-Raphson
    where C = F * coupon_rate / freq, n = years * freq

  Macaulay Duration = sum(t * PV(CF_t)) / Price   (t in periods, result in years = / freq)
  Modified Duration = Macaulay / (1 + ytm/freq)

자료형: pure Decimal (ADR-008 finance = Decimal path)

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, mul, power, sub
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _price_from_ytm(
    face_d: Decimal,
    coupon_d: Decimal,
    n_periods: int,
    y_per_period: Decimal,
) -> Decimal:
    """Compute bond price given yield-per-period."""
    one_plus_y = add(Decimal("1"), y_per_period)
    total      = Decimal("0")
    for t in range(1, n_periods + 1):
        total += div(coupon_d, power(one_plus_y, t))
    total += div(face_d, power(one_plus_y, n_periods))
    return total


def _dprice_from_ytm(
    face_d: Decimal,
    coupon_d: Decimal,
    n_periods: int,
    y_per_period: Decimal,
) -> Decimal:
    """Derivative of bond price with respect to yield-per-period."""
    one_plus_y = add(Decimal("1"), y_per_period)
    total      = Decimal("0")
    for t in range(1, n_periods + 1):
        total -= D(str(t)) * coupon_d / power(one_plus_y, t + 1)
    total -= D(str(n_periods)) * face_d / power(one_plus_y, n_periods + 1)
    return total


@REGISTRY.tool(
    namespace="finance",
    name="bond_ytm",
    description="채권 만기수익률(YTM) 계산. Newton-Raphson 수치해법.",
    version="1.0.0",
)
def bond_ytm(
    price: str,
    face: str,
    coupon_rate: str,
    years: int,
    freq: int = 2,
    max_iter: int = 100,
    tol: str = "1e-10",
) -> dict[str, Any]:
    """Compute the Yield-to-Maturity of a coupon bond.

    Args:
        price:       현재 채권 가격 (Decimal string)
        face:        액면가 (Decimal string)
        coupon_rate: 연 표면이율 e.g. "0.05"
        years:       만기 (년)
        freq:        연 이자지급 횟수 (기본 2 = 반기)
        max_iter:    최대 반복 횟수
        tol:         수렴 허용 오차

    Returns:
        {ytm: str, iterations: int, converged: bool, trace: dict}
    """
    trace = CalcTrace(
        tool="finance.bond_ytm",
        formula=(
            "P = sum(C/(1+y/f)^t, t=1..n) + F/(1+y/f)^n; "
            "C = F*coupon_rate/freq; solve for y via Newton-Raphson"
        ),
    )

    price_d       = D(price)
    face_d        = D(face)
    coupon_rate_d = D(coupon_rate)
    tol_d         = D(tol)

    if price_d <= Decimal("0"):
        raise InvalidInputError("price는 양수여야 합니다.")
    if face_d <= Decimal("0"):
        raise InvalidInputError("face는 양수여야 합니다.")
    if coupon_rate_d < Decimal("0"):
        raise InvalidInputError("coupon_rate는 0 이상이어야 합니다.")
    if years <= 0:
        raise InvalidInputError("years는 1 이상이어야 합니다.")
    if freq <= 0:
        raise InvalidInputError("freq는 1 이상이어야 합니다.")

    trace.input("price",       price)
    trace.input("face",        face)
    trace.input("coupon_rate", coupon_rate)
    trace.input("years",       years)
    trace.input("freq",        freq)

    n_periods = years * freq
    # Coupon per period
    coupon_d  = div(mul(face_d, coupon_rate_d), D(str(freq)))
    trace.step("coupon_per_period", str(coupon_d))
    trace.step("n_periods", str(n_periods))

    # Initial guess: coupon_rate (annual)
    y_annual = coupon_rate_d if coupon_rate_d > Decimal("0") else Decimal("0.05")
    y        = div(y_annual, D(str(freq)))  # per-period yield

    converged  = False
    iterations = 0

    for i in range(max_iter):
        p_calc  = _price_from_ytm(face_d, coupon_d, n_periods, y)
        dp_calc = _dprice_from_ytm(face_d, coupon_d, n_periods, y)

        diff = sub(p_calc, price_d)

        if abs(diff) <= tol_d:
            converged  = True
            iterations = i
            break

        if dp_calc == Decimal("0"):
            break

        y_new = sub(y, div(diff, dp_calc))

        # Clamp: yield-per-period must stay in (-1, inf) for meaningful results
        if y_new <= Decimal("-0.9999"):
            y_new = Decimal("-0.9")

        if abs(y_new - y) < tol_d:
            y          = y_new
            converged  = True
            iterations = i + 1
            break

        y          = y_new
        iterations = i + 1

    # Convert per-period yield back to annual
    ytm_annual = mul(y, D(str(freq)))
    trace.step("ytm_per_period", str(y))
    trace.step("ytm_annual",     str(ytm_annual))
    trace.output(str(ytm_annual))

    return {
        "ytm":        str(ytm_annual),
        "iterations": iterations,
        "converged":  converged,
        "trace":      trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="bond_duration",
    description="Macaulay Duration과 Modified Duration 계산.",
    version="1.0.0",
)
def bond_duration(
    face: str,
    coupon_rate: str,
    years: int,
    ytm: str,
    freq: int = 2,
) -> dict[str, Any]:
    """Compute Macaulay and Modified Duration of a bond.

    Args:
        face:        액면가 (Decimal string)
        coupon_rate: 연 표면이율 e.g. "0.05"
        years:       만기 (년)
        ytm:         연 만기수익률 e.g. "0.05"
        freq:        연 이자지급 횟수

    Returns:
        {macaulay: str, modified: str, trace: dict}
    """
    trace = CalcTrace(
        tool="finance.bond_duration",
        formula=(
            "MacaulayD = sum(t * PV(CF_t)) / Price [in years]; "
            "ModifiedD = MacaulayD / (1 + ytm/freq)"
        ),
    )

    face_d        = D(face)
    coupon_rate_d = D(coupon_rate)
    ytm_d         = D(ytm)

    if face_d <= Decimal("0"):
        raise InvalidInputError("face는 양수여야 합니다.")
    if coupon_rate_d < Decimal("0"):
        raise InvalidInputError("coupon_rate는 0 이상이어야 합니다.")
    if years <= 0:
        raise InvalidInputError("years는 1 이상이어야 합니다.")
    if freq <= 0:
        raise InvalidInputError("freq는 1 이상이어야 합니다.")

    trace.input("face",        face)
    trace.input("coupon_rate", coupon_rate)
    trace.input("years",       years)
    trace.input("ytm",         ytm)
    trace.input("freq",        freq)

    n_periods    = years * freq
    freq_d       = D(str(freq))
    coupon_d     = div(mul(face_d, coupon_rate_d), freq_d)
    y_per_period = div(ytm_d, freq_d)
    one_plus_y   = add(Decimal("1"), y_per_period)

    trace.step("coupon_per_period", str(coupon_d))
    trace.step("y_per_period",      str(y_per_period))

    # Price (PV of all cashflows)
    price  = _price_from_ytm(face_d, coupon_d, n_periods, y_per_period)

    # Macaulay numerator: sum(t_period * PV(CF_t))
    mac_num = Decimal("0")
    for t in range(1, n_periods + 1):
        if t < n_periods:
            cf_pv = div(coupon_d, power(one_plus_y, t))
        else:
            cf_pv = div(add(coupon_d, face_d), power(one_plus_y, t))
        mac_num += D(str(t)) * cf_pv

    # Macaulay duration in periods -> convert to years
    mac_periods = div(mac_num, price)
    mac_years   = div(mac_periods, freq_d)

    # Modified duration
    mod_duration = div(mac_years, add(Decimal("1"), y_per_period))

    trace.step("price",             str(price))
    trace.step("macaulay_periods",  str(mac_periods))
    trace.step("macaulay_years",    str(mac_years))
    trace.step("modified_duration", str(mod_duration))
    trace.output({"macaulay": str(mac_years), "modified": str(mod_duration)})

    return {
        "macaulay": str(mac_years),
        "modified": str(mod_duration),
        "trace":    trace.to_dict(),
    }
