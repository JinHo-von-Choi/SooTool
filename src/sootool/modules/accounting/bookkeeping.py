"""Accounting bookkeeping tools: double-entry balance verification."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


class BalanceResult(TracedResult):
    balanced:     bool
    debit_total:  str
    credit_total: str
    diff:         str


@REGISTRY.tool(
    namespace="accounting",
    name="balance",
    description=(
        "분개 목록의 차변 합계와 대변 합계가 같은지 검증한다. entries 는 {account, debit, credit} 항목의 목록이며 "
        "금액은 Decimal 문자열, 비어 있으면 0 으로 본다. 반환값은 balanced 여부, 두 합계, 차이의 절댓값(diff). "
        "account 는 합계에 쓰이지 않으므로 계정별 잔액 검증에는 쓸 수 없다."
    ),
    version="1.0.0",
)
def balance(entries: list[dict[str, Any]]) -> BalanceResult:
    """Verify that total debits equal total credits across journal entries.

    Args:
        entries: list of {account: str, debit: str, credit: str}

    Returns:
        {balanced, debit_total, credit_total, diff, trace}
    """
    trace = CalcTrace(
        tool="accounting.balance",
        formula="sum(debit) == sum(credit)",
    )
    trace.input("entries", entries)

    debit_vals  = [D(e.get("debit",  "0") or "0") for e in entries]
    credit_vals = [D(e.get("credit", "0") or "0") for e in entries]

    debit_total  = add(*debit_vals)  if debit_vals  else Decimal("0")
    credit_total = add(*credit_vals) if credit_vals else Decimal("0")
    diff         = abs(debit_total - credit_total)
    balanced     = diff == Decimal("0")

    trace.step("debit_total",  str(debit_total))
    trace.step("credit_total", str(credit_total))
    trace.step("diff",         str(diff))
    trace.output({"balanced": balanced, "diff": str(diff)})

    return {
        "balanced":      balanced,
        "debit_total":   str(debit_total),
        "credit_total":  str(credit_total),
        "diff":          str(diff),
        "trace":         trace.to_dict(),
    }
