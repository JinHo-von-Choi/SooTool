"""Derivatives: futures pricing, forward-spot parity, exotic option payoffs.

Author: 최진호
Date: 2026-04-23

All Decimal.  Exponentials use mpmath for forward/futures cost-of-carry.
"""
from __future__ import annotations

from decimal import Decimal
from typing import NotRequired

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


class FinanceFuturesPriceResult(TracedResult):
    futures_price: str
    carry_rate:    str


class FinanceForwardPriceResult(TracedResult):
    forward_price: str


class FinanceOptionPayoffResult(TracedResult):
    payoff:        str
    terminal_spot: str
    is_call:       bool
    option_type:   str
    activated:     NotRequired[bool]

_DEFAULT_DPS = 40


def _q8(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.00000001"))


def _exp_decimal(x: Decimal) -> Decimal:
    """Compute exp(x) via mpmath with fixed precision."""
    mpmath.mp.dps = _DEFAULT_DPS
    out = mpmath.exp(mpmath.mpf(str(x)))
    return mpmath_to_decimal(out, 30)


@REGISTRY.tool(
    namespace="finance",
    name="futures_price",
    description=(
        "연속복리 보유비용 모형의 선물 이론가격을 계산한다. F = S x exp((r - q) x T). spot 은 양수, risk_free_rate 와 "
        "dividend_yield(q, 기본 0)는 연속복리 연율, time_to_expiry 는 0 초과 연 단위, 모두 Decimal 문자열. "
        "결과는 소수 8자리. 이산복리 이율을 그대로 넣으면 값이 어긋난다."
    ),
    version="1.0.0",
)
def finance_futures_price(
    spot:            str,
    risk_free_rate:  str,
    time_to_expiry:  str,
    dividend_yield:  str = "0",
) -> FinanceFuturesPriceResult:
    """Cost-of-carry futures price (continuous compounding).

    F = S * exp((r - q) * T)

    Args:
        spot:           현물가격 (Decimal)
        risk_free_rate: 연속복리 무위험수익률 (Decimal)
        time_to_expiry: 만기(년)
        dividend_yield: 연속복리 배당수익률

    Returns:
        {futures_price, carry_rate, trace}
    """
    trace = CalcTrace(
        tool="finance.futures_price",
        formula="F = S * exp((r - q) * T)",
    )
    s  = D(spot)
    r  = D(risk_free_rate)
    q  = D(dividend_yield)
    t  = D(time_to_expiry)

    if s <= Decimal("0"):
        raise InvalidInputError("spot은 0보다 커야 합니다.")
    if t <= Decimal("0"):
        raise InvalidInputError("time_to_expiry는 0보다 커야 합니다.")

    carry = (r - q) * t
    factor = _exp_decimal(carry)
    fut = s * factor

    trace.input("spot",            spot)
    trace.input("risk_free_rate",  risk_free_rate)
    trace.input("time_to_expiry",  time_to_expiry)
    trace.input("dividend_yield",  dividend_yield)
    trace.step("carry_rate", str(_q8(carry)))
    trace.step("factor",     str(_q8(factor)))
    trace.output(str(_q8(fut)))

    return {
        "futures_price": str(_q8(fut)),
        "carry_rate":    str(_q8(carry)),
        "trace":         trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="forward_price",
    description=(
        "무차익 선도가격을 계산한다. F = S x exp((r - y) x T), 연속복리 기준이며 income_yield(배당률이나 쿠폰수익률, "
        "기본 0)를 차감한다. spot 은 양수, time_to_expiry 는 0 초과 연 단위, 모두 Decimal 문자열이고 결과는 소수 8자리. "
        "이산복리 이율은 연속복리로 환산해서 넣어야 한다."
    ),
    version="1.0.0",
)
def finance_forward_price(
    spot:            str,
    risk_free_rate:  str,
    time_to_expiry:  str,
    income_yield:    str = "0",
) -> FinanceForwardPriceResult:
    """Forward price via cost-of-carry (continuous compounding).

    F = S * exp((r - y) * T) where y is income yield (dividends/coupons).
    """
    trace = CalcTrace(
        tool="finance.forward_price",
        formula="F = S * exp((r - y) * T)",
    )
    s = D(spot)
    r = D(risk_free_rate)
    y = D(income_yield)
    t = D(time_to_expiry)

    if s <= Decimal("0"):
        raise InvalidInputError("spot은 0보다 커야 합니다.")
    if t <= Decimal("0"):
        raise InvalidInputError("time_to_expiry는 0보다 커야 합니다.")

    factor = _exp_decimal((r - y) * t)
    fwd = s * factor

    trace.input("spot",           spot)
    trace.input("risk_free_rate", risk_free_rate)
    trace.input("time_to_expiry", time_to_expiry)
    trace.input("income_yield",   income_yield)
    trace.output(str(_q8(fwd)))

    return {
        "forward_price": str(_q8(fwd)),
        "trace":         trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="finance",
    name="option_payoff",
    description=(
        "옵션의 만기 payoff 를 계산한다. option_type 은 vanilla, digital(현금 지급), asian(산술평균), "
        "barrier(up_in, up_out, down_in, down_out). spot_path 는 기초자산 가격 문자열 목록이며 vanilla 와 digital 은 "
        "마지막 값만 쓴다. barrier 유형은 barrier 와 barrier_type 이 필수이고 결과는 소수 8자리. 만기 가치일 뿐 프리미엄이 아니다."
    ),
    version="1.0.0",
)
def finance_option_payoff(
    option_type:   str,
    strike:        str,
    spot_path:     list[str],
    is_call:       bool = True,
    barrier:       str | None = None,
    barrier_type:  str | None = None,
    digital_cash:  str  = "1",
) -> FinanceOptionPayoffResult:
    """Compute terminal payoff.

    Args:
        option_type:  'vanilla' | 'digital' | 'asian' | 'barrier'
        strike:       행사가
        spot_path:    기초자산 가격 경로 (asian/barrier용). vanilla/digital은
                      마지막 값만 사용.
        is_call:      True=call, False=put
        barrier:      barrier 레벨 (barrier 유형일 때 필수)
        barrier_type: 'up_in' | 'up_out' | 'down_in' | 'down_out' (barrier 유형일 때)
        digital_cash: digital payoff 고정 현금 (기본 1)

    Returns:
        {payoff, terminal_spot, is_call, option_type, activated(opt), trace}
    """
    trace = CalcTrace(
        tool="finance.option_payoff",
        formula=(
            "vanilla: max((S-K) or (K-S), 0); "
            "digital: cash if ITM else 0; "
            "asian: max(mean(path)-K, 0); "
            "barrier: apply knock-in/out before vanilla"
        ),
    )
    if option_type not in ("vanilla", "digital", "asian", "barrier"):
        raise InvalidInputError(
            "option_type은 'vanilla' | 'digital' | 'asian' | 'barrier'."
        )
    if not spot_path:
        raise InvalidInputError("spot_path는 비어있을 수 없습니다.")

    path = [D(s) for s in spot_path]
    k    = D(strike)
    term = path[-1]

    def vanilla_payoff(s: Decimal) -> Decimal:
        return max(s - k, Decimal("0")) if is_call else max(k - s, Decimal("0"))

    activated: bool | None = None

    if option_type == "vanilla":
        payoff = vanilla_payoff(term)

    elif option_type == "digital":
        cash = D(digital_cash)
        in_money = (term > k) if is_call else (term < k)
        payoff = cash if in_money else Decimal("0")

    elif option_type == "asian":
        avg = sum(path, Decimal("0")) / Decimal(len(path))
        payoff = (
            max(avg - k, Decimal("0")) if is_call
            else max(k - avg, Decimal("0"))
        )

    else:  # barrier
        if barrier is None or barrier_type is None:
            raise InvalidInputError("barrier 유형은 barrier/barrier_type 필수.")
        if barrier_type not in ("up_in", "up_out", "down_in", "down_out"):
            raise InvalidInputError(
                "barrier_type은 up_in|up_out|down_in|down_out."
            )
        b = D(barrier)
        if barrier_type.startswith("up"):
            touched = any(s >= b for s in path)
        else:
            touched = any(s <= b for s in path)

        activated = (
            touched if barrier_type.endswith("in") else (not touched)
        )
        payoff = vanilla_payoff(term) if activated else Decimal("0")

    trace.input("option_type",  option_type)
    trace.input("strike",       strike)
    trace.input("spot_path_n",  len(path))
    trace.input("is_call",      is_call)
    trace.input("barrier",      barrier)
    trace.input("barrier_type", barrier_type)
    trace.output(str(_q8(payoff)))

    result: FinanceOptionPayoffResult = {
        "payoff":        str(_q8(payoff)),
        "terminal_spot": str(term),
        "is_call":       is_call,
        "option_type":   option_type,
        "trace":         trace.to_dict(),
    }
    if activated is not None:
        result["activated"] = activated
    return result


__all__ = [
    "finance_futures_price",
    "finance_forward_price",
    "finance_option_payoff",
]
