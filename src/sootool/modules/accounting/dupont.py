"""DuPont decomposition (3-step and 5-step).

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply


def _nonzero(value: Decimal, field: str) -> Decimal:
    if value == Decimal("0"):
        raise InvalidInputError(f"{field}은 0이 아니어야 합니다.")
    return value


@REGISTRY.tool(
    namespace="accounting",
    name="dupont_3",
    description=(
        "DuPont 3단계 분해: ROE = 순이익률 × 총자산회전율 × 재무레버리지. "
        "식별 가능한 원인을 도출."
    ),
    version="1.0.0",
)
def accounting_dupont_3(
    net_income:    str,
    revenue:       str,
    total_assets:  str,
    total_equity:  str,
    decimals:      int = 6,
) -> dict[str, Any]:
    """3-step DuPont: ROE = NM * TAT * EM.

    Returns:
        {net_margin, asset_turnover, equity_multiplier, roe, trace}
    """
    trace = CalcTrace(
        tool="accounting.dupont_3",
        formula="ROE = (NI/Rev) * (Rev/TA) * (TA/TE)",
    )

    ni  = D(net_income)
    rev = D(revenue)
    ta  = D(total_assets)
    te  = D(total_equity)

    rev = _nonzero(rev, "revenue")
    ta  = _nonzero(ta,  "total_assets")
    te  = _nonzero(te,  "total_equity")

    trace.input("net_income",   net_income)
    trace.input("revenue",      revenue)
    trace.input("total_assets", total_assets)
    trace.input("total_equity", total_equity)

    nm  = ni / rev
    tat = rev / ta
    em  = ta / te
    roe = nm * tat * em

    def r(v: Decimal) -> str:
        return str(round_apply(v, decimals, RoundingPolicy.HALF_EVEN))

    out = {
        "net_margin":        r(nm),
        "asset_turnover":    r(tat),
        "equity_multiplier": r(em),
        "roe":               r(roe),
    }
    trace.output(out)
    return {**out, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="accounting",
    name="dupont_5",
    description=(
        "DuPont 5단계 분해: ROE = 세부담비율 × 이자부담비율 × "
        "영업이익률 × 총자산회전율 × 재무레버리지."
    ),
    version="1.0.0",
)
def accounting_dupont_5(
    net_income:    str,
    pretax_income: str,
    ebit:          str,
    revenue:       str,
    total_assets:  str,
    total_equity:  str,
    decimals:      int = 6,
) -> dict[str, Any]:
    """5-step DuPont.

    ROE = (NI/EBT) * (EBT/EBIT) * (EBIT/Rev) * (Rev/TA) * (TA/TE)
    """
    trace = CalcTrace(
        tool="accounting.dupont_5",
        formula=(
            "ROE = (NI/EBT) * (EBT/EBIT) * (EBIT/Rev) * (Rev/TA) * (TA/TE)"
        ),
    )

    ni_d   = D(net_income)
    ebt_d  = D(pretax_income)
    ebit_d = D(ebit)
    rev_d  = D(revenue)
    ta_d   = D(total_assets)
    te_d   = D(total_equity)

    ebt_d  = _nonzero(ebt_d,  "pretax_income")
    ebit_d = _nonzero(ebit_d, "ebit")
    rev_d  = _nonzero(rev_d,  "revenue")
    ta_d   = _nonzero(ta_d,   "total_assets")
    te_d   = _nonzero(te_d,   "total_equity")

    trace.input("net_income",    net_income)
    trace.input("pretax_income", pretax_income)
    trace.input("ebit",          ebit)
    trace.input("revenue",       revenue)
    trace.input("total_assets",  total_assets)
    trace.input("total_equity",  total_equity)

    tax_burden        = ni_d / ebt_d
    interest_burden   = ebt_d / ebit_d
    operating_margin  = ebit_d / rev_d
    asset_turnover    = rev_d / ta_d
    equity_multiplier = ta_d / te_d
    roe = tax_burden * interest_burden * operating_margin * asset_turnover * equity_multiplier

    def r(v: Decimal) -> str:
        return str(round_apply(v, decimals, RoundingPolicy.HALF_EVEN))

    out = {
        "tax_burden":        r(tax_burden),
        "interest_burden":   r(interest_burden),
        "operating_margin":  r(operating_margin),
        "asset_turnover":    r(asset_turnover),
        "equity_multiplier": r(equity_multiplier),
        "roe":               r(roe),
    }
    trace.output(out)
    return {**out, "trace": trace.to_dict()}
