"""Accounting bookkeeping tools: double-entry balance verification."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add
from sootool.core.registry import REGISTRY


@REGISTRY.tool(
    namespace="accounting",
    name="balance",
    description="차변/대변 합계 균형 검증. balanced=false 시 diff 제공.",
    version="1.0.0",
)
def balance(entries: list[dict[str, Any]]) -> dict[str, Any]:
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
