"""Finance metrics tools: NPV and IRR.

공식 출처: Brealey, Myers & Allen, "Principles of Corporate Finance", 13th ed.
  NPV = sum(CF_t / (1+r)^t) for t = 0..n
  IRR: solve NPV(r) = 0 using Newton-Raphson with bisection fallback.

자료형: pure Decimal (ADR-008 finance = Decimal path)
반올림 정책: HALF_EVEN (기본)

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, power
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy, apply


def _parse_policy(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(f"유효하지 않은 반올림 정책: {rounding!r}") from exc


def _npv_decimal(rate_d: Decimal, cashflows_d: list[Decimal]) -> Decimal:
    """Compute NPV given a Decimal rate and list of Decimal cashflows."""
    total  = Decimal("0")
    one_pr = add(Decimal("1"), rate_d)
    for t, cf in enumerate(cashflows_d):
        if t == 0:
            total += cf
        else:
            total += div(cf, power(one_pr, t))
    return total


def _dnpv_decimal(rate_d: Decimal, cashflows_d: list[Decimal]) -> Decimal:
    """Compute derivative of NPV with respect to rate (for Newton-Raphson)."""
    total  = Decimal("0")
    one_pr = add(Decimal("1"), rate_d)
    for t, cf in enumerate(cashflows_d):
        if t == 0:
            continue
        # d/dr [CF / (1+r)^t] = -t * CF / (1+r)^(t+1)
        total -= D(str(t)) * cf / power(one_pr, t + 1)
    return total


@REGISTRY.tool(
    namespace="finance",
    name="npv",
    description="순현재가치(NPV) 계산. NPV = sum(CF_t / (1+r)^t)",
    version="1.0.0",
)
def npv(
    rate: str,
    cashflows: list[str],
    rounding: str = "HALF_EVEN",
    decimals: int = 2,
) -> dict[str, Any]:
    """Compute Net Present Value.

    Args:
        rate:       할인율 (Decimal string, >= 0)
        cashflows:  현금흐름 목록. index 0 = t=0 (초기 투자는 음수).
        rounding:   반올림 정책
        decimals:   반올림 소수점 자릿수

    Returns:
        {npv: str, trace: dict}
    """
    trace = CalcTrace(
        tool="finance.npv",
        formula="NPV = sum(CF_t / (1+r)^t, t=0..n)",
    )
    policy = _parse_policy(rounding)

    if not cashflows:
        raise InvalidInputError("cashflows는 최소 1개 이상이어야 합니다.")

    rate_d = D(rate)
    if rate_d < Decimal("0"):
        raise InvalidInputError("rate는 0 이상이어야 합니다.")

    cashflows_d = [D(cf) for cf in cashflows]

    trace.input("rate",       rate)
    trace.input("cashflows",  cashflows)
    trace.input("rounding",   rounding)
    trace.input("decimals",   decimals)

    npv_raw = _npv_decimal(rate_d, cashflows_d)
    trace.step("npv_raw", str(npv_raw))

    npv_val = apply(npv_raw, decimals, policy)
    trace.output(str(npv_val))

    return {
        "npv":   str(npv_val),
        "trace": trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="irr",
    description="내부수익률(IRR) 계산. Newton-Raphson + 이분법 폴백.",
    version="1.0.0",
)
def irr(
    cashflows: list[str],
    guess: str = "0.1",
    max_iter: int = 100,
    tol: str = "1e-10",
) -> dict[str, Any]:
    """Compute Internal Rate of Return.

    Uses Newton-Raphson first; falls back to bisection over [-0.99, 10]
    if Newton-Raphson diverges. Returns converged=False if no sign change exists.

    Args:
        cashflows: 현금흐름 목록. index 0 = t=0.
        guess:     초기 추정치 (기본 "0.1")
        max_iter:  최대 반복 횟수
        tol:       수렴 허용 오차

    Returns:
        {irr: str | None, iterations: int, converged: bool, trace: dict}
    """
    trace = CalcTrace(
        tool="finance.irr",
        formula="solve NPV(r)=0 via Newton-Raphson; bisection fallback",
    )

    if len(cashflows) < 2:
        raise InvalidInputError("cashflows는 최소 2개 이상이어야 합니다.")

    cashflows_d = [D(cf) for cf in cashflows]
    tol_d       = D(tol)
    guess_d     = D(guess)

    trace.input("cashflows", cashflows)
    trace.input("guess",     guess)
    trace.input("max_iter",  max_iter)
    trace.input("tol",       tol)

    # Check sign change: need at least one positive and one negative cashflow
    has_positive = any(cf > Decimal("0") for cf in cashflows_d)
    has_negative = any(cf < Decimal("0") for cf in cashflows_d)
    if not (has_positive and has_negative):
        trace.step("result", "no_sign_change")
        trace.output("converged=False")
        return {
            "irr":        None,
            "iterations": 0,
            "converged":  False,
            "trace":      trace.to_dict(),
        }

    # Newton-Raphson
    r        = guess_d
    converged = False
    iterations = 0
    for i in range(max_iter):
        npv_val  = _npv_decimal(r, cashflows_d)
        dnpv_val = _dnpv_decimal(r, cashflows_d)

        if abs(npv_val) <= tol_d:
            converged  = True
            iterations = i
            break

        if dnpv_val == Decimal("0"):
            # Derivative is zero; switch to bisection
            break

        r_new = r - div(npv_val, dnpv_val)

        # Clamp to reasonable range to avoid divergence
        if r_new < Decimal("-0.99"):
            r_new = Decimal("-0.99")
        if r_new > Decimal("100"):
            r_new = Decimal("100")

        if abs(r_new - r) < tol_d:
            r          = r_new
            converged  = True
            iterations = i + 1
            break

        r          = r_new
        iterations = i + 1

    if converged:
        trace.step("method",     "newton_raphson")
        trace.step("iterations", str(iterations))
        trace.step("irr",        str(r))
        trace.output(str(r))
        return {
            "irr":        str(r),
            "iterations": iterations,
            "converged":  True,
            "trace":      trace.to_dict(),
        }

    # Bisection fallback over [-0.99, 10]
    lo = Decimal("-0.99")
    hi = Decimal("10")

    npv_lo = _npv_decimal(lo, cashflows_d)
    npv_hi = _npv_decimal(hi, cashflows_d)

    if (npv_lo > 0) == (npv_hi > 0):
        # No sign change in bisection range either
        trace.step("result", "bisection_no_sign_change")
        trace.output("converged=False")
        return {
            "irr":        None,
            "iterations": iterations,
            "converged":  False,
            "trace":      trace.to_dict(),
        }

    bisect_iters = 0
    for _ in range(200):
        mid     = div(lo + hi, Decimal("2"))
        npv_mid = _npv_decimal(mid, cashflows_d)

        if abs(npv_mid) <= tol_d:
            converged     = True
            r             = mid
            bisect_iters += 1
            break

        if (npv_lo > 0) == (npv_mid > 0):
            lo     = mid
            npv_lo = npv_mid
        else:
            hi = mid

        bisect_iters += 1
        if abs(hi - lo) < tol_d:
            converged = True
            r         = mid
            break

    total_iters = iterations + bisect_iters
    trace.step("method",     "bisection")
    trace.step("iterations", str(total_iters))

    if converged:
        trace.step("irr", str(r))
        trace.output(str(r))
        return {
            "irr":        str(r),
            "iterations": total_iters,
            "converged":  True,
            "trace":      trace.to_dict(),
        }

    trace.output("converged=False")
    return {
        "irr":        None,
        "iterations": total_iters,
        "converged":  False,
        "trace":      trace.to_dict(),
    }
