"""Currency FX conversion tools with ISO 4217 minor-unit decimal rules."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy, apply

# ISO 4217 minor units — number of decimal places for final rounding.
# 0-decimal: whole-unit currencies (no sub-unit).
# 2-decimal: most major currencies.
# 3-decimal: dinar-family currencies.
CURRENCY_DECIMALS: dict[str, int] = {
    # 0-decimal currencies
    "JPY": 0,
    "KRW": 0,
    "CLP": 0,
    "ISK": 0,
    "UGX": 0,
    "VND": 0,
    "BIF": 0,
    "COP": 0,
    "DJF": 0,
    "GNF": 0,
    "KMF": 0,
    "MGA": 0,
    "PYG": 0,
    "RWF": 0,
    "VUV": 0,
    "XAF": 0,
    "XOF": 0,
    "XPF": 0,
    # 2-decimal currencies (most common)
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "AUD": 2,
    "CNY": 2,
    "HKD": 2,
    "CAD": 2,
    "SGD": 2,
    "CHF": 2,
    "SEK": 2,
    "NOK": 2,
    "DKK": 2,
    "NZD": 2,
    "MXN": 2,
    "INR": 2,
    "BRL": 2,
    "RUB": 2,
    "ZAR": 2,
    "TRY": 2,
    "THB": 2,
    "IDR": 2,
    "MYR": 2,
    "PHP": 2,
    "EGP": 2,
    "PLN": 2,
    "CZK": 2,
    "HUF": 2,
    "RON": 2,
    "AED": 2,
    "SAR": 2,
    "QAR": 2,
    "PKR": 2,
    "NGN": 2,
    "UAH": 2,
    # 3-decimal currencies (dinar-family)
    "BHD": 3,
    "KWD": 3,
    "OMR": 3,
    "TND": 3,
    "JOD": 3,
    "IQD": 3,
    "LYD": 3,
}

_DEFAULT_DECIMALS = 2


def _currency_decimals(ccy: str) -> int:
    """Return the number of minor-unit decimal places for a currency code."""
    return CURRENCY_DECIMALS.get(ccy.upper(), _DEFAULT_DECIMALS)


def _parse_policy(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(f"유효하지 않은 반올림 정책: {rounding!r}") from exc


@REGISTRY.tool(
    namespace="units",
    name="fx_convert",
    description="FX direct conversion: amount * rate, rounded to to_ccy minor units.",
    version="1.0.0",
)
def fx_convert(
    amount: str,
    from_ccy: str,
    to_ccy: str,
    rate: str,
    rounding: str = "HALF_EVEN",
) -> dict[str, Any]:
    """Convert an amount from one currency to another using a direct exchange rate.

    Formula: result = amount * rate, rounded to to_ccy decimal places.

    Args:
        amount:   Source amount (Decimal string).
        from_ccy: Source currency code (ISO 4217, e.g. "KRW").
        to_ccy:   Target currency code (ISO 4217, e.g. "USD").
        rate:     Exchange rate from from_ccy to to_ccy (Decimal string).
        rounding: Rounding policy applied to final amount (default HALF_EVEN).

    Returns:
        {amount: str, currency: str, trace}
    """
    trace = CalcTrace(
        tool="units.fx_convert",
        formula="result = amount * rate [rounded to to_ccy decimals]",
    )
    policy  = _parse_policy(rounding)
    amount_d = D(amount)
    rate_d   = D(rate)

    if rate_d <= Decimal("0"):
        raise InvalidInputError("rate는 0 초과여야 합니다.")
    if amount_d < Decimal("0"):
        raise InvalidInputError("amount는 0 이상이어야 합니다.")

    from_upper = from_ccy.upper()
    to_upper   = to_ccy.upper()
    decimals   = _currency_decimals(to_upper)

    trace.input("amount",   amount)
    trace.input("from_ccy", from_upper)
    trace.input("to_ccy",   to_upper)
    trace.input("rate",     rate)
    trace.input("rounding", rounding)

    raw    = mul(amount_d, rate_d)
    result = apply(raw, decimals, policy)

    trace.step("raw",      str(raw))
    trace.step("decimals", decimals)
    trace.step("result",   str(result))
    trace.output({"amount": str(result), "currency": to_upper})

    return {
        "amount":   str(result),
        "currency": to_upper,
        "trace":    trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="units",
    name="fx_triangulate",
    description="Triangulated FX: from_ccy → via_ccy → to_ccy using two rates.",
    version="1.0.0",
)
def fx_triangulate(
    amount: str,
    from_ccy: str,
    via_ccy: str,
    to_ccy: str,
    rate1: str,
    rate2: str,
    rounding: str = "HALF_EVEN",
) -> dict[str, Any]:
    """Convert an amount through an intermediate currency (triangulation).

    Formula: intermediate = amount * rate1; result = intermediate * rate2,
    rounded to to_ccy decimal places.

    Args:
        amount:   Source amount (Decimal string).
        from_ccy: Source currency (e.g. "KRW").
        via_ccy:  Intermediate currency (e.g. "USD").
        to_ccy:   Target currency (e.g. "JPY").
        rate1:    Rate from from_ccy to via_ccy.
        rate2:    Rate from via_ccy to to_ccy.
        rounding: Rounding policy for final result (default HALF_EVEN).

    Returns:
        {amount: str, currency: str, trace}
    """
    trace = CalcTrace(
        tool="units.fx_triangulate",
        formula="via = amount * rate1; result = via * rate2 [rounded to to_ccy decimals]",
    )
    policy  = _parse_policy(rounding)
    amount_d = D(amount)
    rate1_d  = D(rate1)
    rate2_d  = D(rate2)

    if rate1_d <= Decimal("0") or rate2_d <= Decimal("0"):
        raise InvalidInputError("rate1과 rate2는 모두 0 초과여야 합니다.")
    if amount_d < Decimal("0"):
        raise InvalidInputError("amount는 0 이상이어야 합니다.")

    from_upper = from_ccy.upper()
    via_upper  = via_ccy.upper()
    to_upper   = to_ccy.upper()
    decimals   = _currency_decimals(to_upper)

    trace.input("amount",   amount)
    trace.input("from_ccy", from_upper)
    trace.input("via_ccy",  via_upper)
    trace.input("to_ccy",   to_upper)
    trace.input("rate1",    rate1)
    trace.input("rate2",    rate2)
    trace.input("rounding", rounding)

    via_amount = mul(amount_d, rate1_d)
    raw        = mul(via_amount, rate2_d)
    result     = apply(raw, decimals, policy)

    trace.step("via_amount", str(via_amount))
    trace.step("raw",        str(raw))
    trace.step("decimals",   decimals)
    trace.step("result",     str(result))
    trace.output({"amount": str(result), "currency": to_upper})

    return {
        "amount":   str(result),
        "currency": to_upper,
        "trace":    trace.to_dict(),
    }
