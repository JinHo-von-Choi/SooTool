"""Tests for accounting.balance tool."""
from __future__ import annotations

import pytest

import sootool.modules.accounting  # ensure tools are registered
from sootool.core.batch import BatchExecutor
from sootool.core.registry import REGISTRY


def _balance(*pairs: tuple[str, str], accounts: list[str] | None = None) -> dict:
    entries = []
    for i, (debit, credit) in enumerate(pairs):
        entries.append({
            "account": (accounts[i] if accounts else f"A{i}"),
            "debit":   debit,
            "credit":  credit,
        })
    return REGISTRY.invoke("accounting.balance", entries=entries)


class TestBalancePerfect:
    def test_simple_balanced(self) -> None:
        result = _balance(("100", "0"), ("0", "100"))
        assert result["balanced"] is True
        assert result["diff"] == "0"
        assert result["debit_total"] == "100"
        assert result["credit_total"] == "100"

    def test_multiple_entries_balanced(self) -> None:
        result = _balance(
            ("500", "0"),
            ("200", "0"),
            ("0", "700"),
        )
        assert result["balanced"] is True
        assert result["diff"] == "0"

    def test_trace_present(self) -> None:
        result = _balance(("50", "50"))
        assert "trace" in result
        trace = result["trace"]
        assert trace["tool"] == "accounting.balance"


class TestBalanceMismatch:
    def test_balance_detects_1won_mismatch(self) -> None:
        """100원 차변, 99.99원 대변 → balanced=false, diff=0.01"""
        result = _balance(("100", "0"), ("0", "99.99"))
        assert result["balanced"] is False
        assert result["diff"] == "0.01"
        assert result["debit_total"] == "100"
        assert result["credit_total"] == "99.99"

    def test_large_mismatch(self) -> None:
        result = _balance(("1000000", "0"), ("0", "999999"))
        assert result["balanced"] is False
        assert result["diff"] == "1"

    def test_zero_entries(self) -> None:
        result = _balance()
        assert result["balanced"] is True
        assert result["debit_total"] == "0"
        assert result["credit_total"] == "0"
        assert result["diff"] == "0"


class TestAccountingBatchRaceFree:
    def test_accounting_balance_core_batch_race_free(self) -> None:
        """Run balance in 100 parallel core.batch calls; all results identical (ADR-007)."""
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"item-{i}",
                "tool": "accounting.balance",
                "args": {
                    "entries": [
                        {"account": "현금", "debit": "100000", "credit": "0"},
                        {"account": "매출", "debit": "0",      "credit": "100000"},
                    ]
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["balanced"] == first["balanced"]
            assert r["diff"] == first["diff"]
            assert r["debit_total"] == first["debit_total"]
            assert r["credit_total"] == first["credit_total"]
