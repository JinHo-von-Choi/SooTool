"""Financial ratios: liquidity, leverage, profitability.

Author: 최진호
Date: 2026-04-23

All inputs/outputs Decimal strings. No float. (ADR-008)
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


def _safe_div(numerator: Decimal, denominator: Decimal, field: str) -> Decimal:
    if denominator == Decimal("0"):
        raise InvalidInputError(f"{field}은 0이 아니어야 합니다.")
    return numerator / denominator


@REGISTRY.tool(
    namespace="accounting",
    name="ratios",
    description=(
        "재무비율 일괄 계산: 유동비율·당좌비율·부채비율·자기자본비율·ROE·ROA. "
        "정규정 재무제표 항목을 입력받아 8개 비율 반환."
    ),
    version="1.0.0",
)
def accounting_ratios(
    current_assets:        str,
    current_liabilities:   str,
    inventory:             str,
    total_assets:          str,
    total_liabilities:     str,
    total_equity:          str,
    net_income:            str,
    revenue:               str,
    decimals:              int = 4,
) -> dict[str, Any]:
    """Compute 8 financial ratios from a balance-sheet + income snapshot.

    Returns:
        {current_ratio, quick_ratio, debt_to_equity, debt_ratio, equity_ratio,
         roe, roa, net_margin, trace}
    """
    trace = CalcTrace(
        tool="accounting.ratios",
        formula=(
            "current_ratio = 유동자산/유동부채; "
            "quick_ratio = (유동자산-재고)/유동부채; "
            "debt_to_equity = 총부채/자기자본; "
            "debt_ratio = 총부채/총자산; "
            "equity_ratio = 자기자본/총자산; "
            "ROE = 당기순이익/자기자본; "
            "ROA = 당기순이익/총자산; "
            "net_margin = 당기순이익/매출"
        ),
    )

    ca  = D(current_assets)
    cl  = D(current_liabilities)
    inv = D(inventory)
    ta  = D(total_assets)
    tl  = D(total_liabilities)
    te  = D(total_equity)
    ni  = D(net_income)
    rev = D(revenue)

    if ca < Decimal("0") or cl < Decimal("0") or inv < Decimal("0") or ta < Decimal("0"):
        raise InvalidInputError("자산·부채·재고는 0 이상이어야 합니다.")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    trace.input("current_assets",      current_assets)
    trace.input("current_liabilities", current_liabilities)
    trace.input("inventory",           inventory)
    trace.input("total_assets",        total_assets)
    trace.input("total_liabilities",   total_liabilities)
    trace.input("total_equity",        total_equity)
    trace.input("net_income",          net_income)
    trace.input("revenue",             revenue)

    cr  = round_apply(_safe_div(ca, cl, "current_liabilities"), decimals, RoundingPolicy.HALF_EVEN)
    qr  = round_apply(_safe_div(ca - inv, cl, "current_liabilities"), decimals, RoundingPolicy.HALF_EVEN)
    de_ = round_apply(_safe_div(tl, te, "total_equity"), decimals, RoundingPolicy.HALF_EVEN)
    dr  = round_apply(_safe_div(tl, ta, "total_assets"), decimals, RoundingPolicy.HALF_EVEN)
    er  = round_apply(_safe_div(te, ta, "total_assets"), decimals, RoundingPolicy.HALF_EVEN)
    roe = round_apply(_safe_div(ni, te, "total_equity"), decimals, RoundingPolicy.HALF_EVEN)
    roa = round_apply(_safe_div(ni, ta, "total_assets"), decimals, RoundingPolicy.HALF_EVEN)
    nm  = round_apply(_safe_div(ni, rev, "revenue"), decimals, RoundingPolicy.HALF_EVEN)

    out = {
        "current_ratio":   str(cr),
        "quick_ratio":     str(qr),
        "debt_to_equity":  str(de_),
        "debt_ratio":      str(dr),
        "equity_ratio":    str(er),
        "roe":             str(roe),
        "roa":             str(roa),
        "net_margin":      str(nm),
    }
    trace.output(out)
    return {**out, "trace": trace.to_dict()}
