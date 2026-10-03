"""Indirect-method operating cash flow.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal
from typing import TypedDict

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


class CashflowBreakdown(TypedDict):
    net_income:      str
    noncash_add:     str
    working_capital: str
    receivables_adj: str
    inventory_adj:   str
    payables_adj:    str
    other_wc_adj:    str


class AccountingCashflowOperatingResult(TracedResult):
    cfo:       str
    breakdown: CashflowBreakdown


@REGISTRY.tool(
    namespace="accounting",
    name="cashflow_operating",
    description=(
        "간접법 영업활동현금흐름(CFO)을 계산한다. 당기순이익에 감가상각비, 무형자산상각비, 기타 비현금 항목을 더하고 "
        "매출채권 증가와 재고자산 증가는 빼며 매입채무 증가는 더한다. 금액은 Decimal 문자열이며 반올림하지 않는다. "
        "증가는 양수로 넣어야 하며 증가분을 음수로 넣으면 부호가 뒤집힌다."
    ),
    version="1.0.0",
)
def accounting_cashflow_operating(
    net_income:                str,
    depreciation:              str = "0",
    amortization:              str = "0",
    other_noncash:             str = "0",
    change_in_receivables:     str = "0",
    change_in_inventory:       str = "0",
    change_in_payables:        str = "0",
    change_in_other_wc:        str = "0",
) -> AccountingCashflowOperatingResult:
    """Indirect-method CFO.

    CFO = NI + 감가상각 + 무형자산상각 + 기타 비현금 항목
        - 매출채권 증가분 - 재고자산 증가분 + 매입채무 증가분 + 기타 운전자본 변동분

    Args:
        net_income:              당기순이익
        depreciation:            감가상각비
        amortization:            무형자산상각비
        other_noncash:           기타 비현금 항목 (주식보상비용 등)
        change_in_receivables:   매출채권 증가(+) 또는 감소(-) — 증가면 현금 감소
        change_in_inventory:     재고자산 증가(+) 또는 감소(-) — 증가면 현금 감소
        change_in_payables:      매입채무 증가(+) 또는 감소(-) — 증가면 현금 증가
        change_in_other_wc:      기타 운전자본 순변동 (부호 convention: 현금 증감 기준)

    Returns:
        {cfo, breakdown, trace}
    """
    trace = CalcTrace(
        tool="accounting.cashflow_operating",
        formula=(
            "CFO = NI + DA + 비현금 ± 운전자본 변동"
        ),
    )

    ni        = D(net_income)
    dep       = D(depreciation)
    amort     = D(amortization)
    other_nc  = D(other_noncash)
    d_ar      = D(change_in_receivables)
    d_inv     = D(change_in_inventory)
    d_ap      = D(change_in_payables)
    d_wc      = D(change_in_other_wc)

    trace.input("net_income",            net_income)
    trace.input("depreciation",          depreciation)
    trace.input("amortization",          amortization)
    trace.input("other_noncash",         other_noncash)
    trace.input("change_in_receivables", change_in_receivables)
    trace.input("change_in_inventory",   change_in_inventory)
    trace.input("change_in_payables",    change_in_payables)
    trace.input("change_in_other_wc",    change_in_other_wc)

    noncash_add = dep + amort + other_nc
    wc_adjust   = (-d_ar) + (-d_inv) + d_ap + d_wc

    cfo: Decimal = ni + noncash_add + wc_adjust

    breakdown: CashflowBreakdown = {
        "net_income":       str(ni),
        "noncash_add":      str(noncash_add),
        "working_capital":  str(wc_adjust),
        "receivables_adj":  str(-d_ar),
        "inventory_adj":    str(-d_inv),
        "payables_adj":     str(d_ap),
        "other_wc_adj":     str(d_wc),
    }
    trace.step("breakdown", breakdown)
    trace.output(str(cfo))

    return {
        "cfo":       str(cfo),
        "breakdown": breakdown,
        "trace":     trace.to_dict(),
    }
