"""DuPont decomposition (3-step and 5-step).

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply


class AccountingDupont3Result(TracedResult):
    net_margin:        str
    asset_turnover:    str
    equity_multiplier: str
    roe:               str


class AccountingDupont5Result(TracedResult):
    tax_burden:        str
    interest_burden:   str
    operating_margin:  str
    asset_turnover:    str
    equity_multiplier: str
    roe:               str


def _nonzero(value: Decimal, field: str) -> Decimal:
    if value == Decimal("0"):
        raise InvalidInputError(f"{field}은 0이 아니어야 합니다.")
    return value


@REGISTRY.tool(
    namespace="accounting",
    name="dupont_3",
    description=(
        "DuPont 3단계 분해로 ROE = 순이익률 x 총자산회전율 x 자기자본승수(재무레버리지)를 계산한다. "
        "금액은 Decimal 문자열이며 매출, 총자산, 자기자본은 0 이 아니어야 한다. 각 값은 decimals(기본 6)자리 HALF_EVEN "
        "반올림이고 음수 자기자본은 막지 않으므로 부호를 확인해야 한다."
    ),
    version="1.0.0",
)
def accounting_dupont_3(
    net_income:    str,
    revenue:       str,
    total_assets:  str,
    total_equity:  str,
    decimals:      int = 6,
) -> AccountingDupont3Result:
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
    return {
        "net_margin": out["net_margin"],
        "asset_turnover": out["asset_turnover"],
        "equity_multiplier": out["equity_multiplier"],
        "roe": out["roe"],
        "trace": trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="accounting",
    name="dupont_5",
    description=(
        "DuPont 5단계 분해로 ROE = 세부담비율(순이익/세전이익) x 이자부담비율(세전이익/EBIT) x 영업이익률 x "
        "총자산회전율 x 재무레버리지를 계산한다. 금액은 Decimal 문자열이며 세전이익, EBIT, 매출, 총자산, 자기자본은 "
        "0 이 아니어야 한다. 각 값은 decimals(기본 6)자리 HALF_EVEN 반올림이다."
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
) -> AccountingDupont5Result:
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
    return {
        "tax_burden": out["tax_burden"],
        "interest_burden": out["interest_burden"],
        "operating_margin": out["operating_margin"],
        "asset_turnover": out["asset_turnover"],
        "equity_multiplier": out["equity_multiplier"],
        "roe": out["roe"],
        "trace": trace.to_dict(),
    }
