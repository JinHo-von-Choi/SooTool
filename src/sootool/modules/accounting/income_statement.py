"""Multi-step income statement.

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


class AccountingIncomeStatementResult(TracedResult):
    gross_profit:     str
    gross_margin:     str
    operating_income: str
    operating_margin: str
    pretax_income:    str
    pretax_margin:    str
    net_income:       str
    net_margin:       str


@REGISTRY.tool(
    namespace="accounting",
    name="income_statement",
    description=(
        "다단계 손익계산서: 매출에서 매출총이익, 영업이익, 세전이익, 당기순이익까지 단계별 이익과 이익률을 계산한다. "
        "금액은 Decimal 문자열이며 매출과 매출원가는 0 이상이어야 한다. 이익은 반올림하지 않고 이익률은 소수 6자리 "
        "(0.25 = 25%)로 반올림하며 매출이 0 이면 0 이다. 비용 항목은 양수로 입력한다."
    ),
    version="1.0.0",
)
def accounting_income_statement(
    revenue:               str,
    cost_of_sales:         str,
    operating_expenses:    str = "0",
    other_income:          str = "0",
    other_expenses:        str = "0",
    interest_expense:      str = "0",
    tax_expense:           str = "0",
) -> AccountingIncomeStatementResult:
    """Build a multi-step income statement from raw line items.

    Flow:
        매출(revenue) - 매출원가(COGS) = 매출총이익(gross_profit)
        매출총이익 - 판관비(opex) = 영업이익(operating_income)
        영업이익 + other_income - other_expenses - interest_expense = 세전이익(pretax)
        세전이익 - 법인세(tax) = 당기순이익(net_income)

    Returns:
        {gross_profit, gross_margin, operating_income, operating_margin,
         pretax_income, pretax_margin, net_income, net_margin, trace}
    """
    trace = CalcTrace(
        tool="accounting.income_statement",
        formula=(
            "매출총이익 = 매출 - 매출원가; "
            "영업이익 = 매출총이익 - 판관비; "
            "세전이익 = 영업이익 + 기타수익 - 기타비용 - 이자비용; "
            "당기순이익 = 세전이익 - 법인세"
        ),
    )

    rev    = D(revenue)
    cogs   = D(cost_of_sales)
    opex   = D(operating_expenses)
    oi     = D(other_income)
    oe     = D(other_expenses)
    interest = D(interest_expense)
    tax    = D(tax_expense)

    if rev < Decimal("0"):
        raise InvalidInputError("revenue는 0 이상이어야 합니다.")
    if cogs < Decimal("0"):
        raise InvalidInputError("cost_of_sales는 0 이상이어야 합니다.")

    trace.input("revenue",            revenue)
    trace.input("cost_of_sales",      cost_of_sales)
    trace.input("operating_expenses", operating_expenses)
    trace.input("other_income",       other_income)
    trace.input("other_expenses",     other_expenses)
    trace.input("interest_expense",   interest_expense)
    trace.input("tax_expense",        tax_expense)

    gross_profit     = rev - cogs
    operating_income = gross_profit - opex
    pretax_income    = operating_income + oi - oe - interest
    net_income       = pretax_income - tax

    def margin(v: Decimal) -> str:
        if rev == Decimal("0"):
            return "0"
        m = v / rev
        return str(m.quantize(Decimal("0.000001")))

    out = {
        "gross_profit":     str(gross_profit),
        "gross_margin":     margin(gross_profit),
        "operating_income": str(operating_income),
        "operating_margin": margin(operating_income),
        "pretax_income":    str(pretax_income),
        "pretax_margin":    margin(pretax_income),
        "net_income":       str(net_income),
        "net_margin":       margin(net_income),
    }
    trace.output(out)
    return {
        "gross_profit": out["gross_profit"],
        "gross_margin": out["gross_margin"],
        "operating_income": out["operating_income"],
        "operating_margin": out["operating_margin"],
        "pretax_income": out["pretax_income"],
        "pretax_margin": out["pretax_margin"],
        "net_income": out["net_income"],
        "net_margin": out["net_margin"],
        "trace": trace.to_dict(),
    }
