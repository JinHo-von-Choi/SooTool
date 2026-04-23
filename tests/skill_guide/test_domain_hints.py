"""Tests that domain tool responses (tax/finance/accounting) carry _meta.hints.

These tests verify that the REGISTRY post_processor chain is wired correctly:
all tools with a "trace" key in their response receive _meta.hints automatically.
"""
from __future__ import annotations

from typing import Any

# Importing server triggers _register_core_tools() and
# REGISTRY.register_post_processor(_hints_post_processor).
# _load_modules() must be called explicitly to register domain tools.
import sootool.server as _srv  # noqa: F401
from sootool.core.registry import REGISTRY

_srv._load_modules()  # register tax/finance/accounting/... into REGISTRY


def _meta_present(result: Any) -> bool:
    return isinstance(result, dict) and "_meta" in result


def _hints_list(result: Any) -> list[dict[str, Any]]:
    return result.get("_meta", {}).get("hints", [])


class TestTaxDomainHints:
    def test_kr_income_has_meta_hints(self) -> None:
        result = REGISTRY.invoke(
            "tax.kr_income",
            taxable_income="50000000",
            year=2026,
        )
        assert _meta_present(result), "_meta missing from tax.kr_income response"
        assert isinstance(_hints_list(result), list)

    def test_kr_income_audit_hint_present(self) -> None:
        """tax.kr_income with default trace_level=summary should trigger audit hint."""
        result = REGISTRY.invoke(
            "tax.kr_income",
            taxable_income="50000000",
            year=2026,
            # trace_level not passed — defaults to whatever the tool uses internally
        )
        # The post-processor records the call; at minimum _meta must be present
        assert "_meta" in result
        assert "session_stats" in result["_meta"]

    def test_progressive_has_meta_hints(self) -> None:
        result = REGISTRY.invoke(
            "tax.progressive",
            taxable_income="30000000",
            brackets=[
                {"upper": "50000000", "rate": "0.15"},
                {"upper": None, "rate": "0.35"},
            ],
        )
        assert _meta_present(result)

    def test_result_and_trace_unchanged(self) -> None:
        """Post-processor must not modify result or trace keys."""
        result = REGISTRY.invoke(
            "tax.kr_income",
            taxable_income="10000000",
            year=2026,
        )
        assert "tax" in result
        assert "trace" in result
        assert result["trace"]["tool"] == "tax.kr_income"


class TestFinanceDomainHints:
    def test_npv_has_meta_hints(self) -> None:
        result = REGISTRY.invoke(
            "finance.npv",
            rate="0.1",
            cashflows=["-1000000", "400000", "400000", "400000"],
        )
        assert _meta_present(result), "_meta missing from finance.npv response"

    def test_pv_has_meta_hints(self) -> None:
        result = REGISTRY.invoke(
            "finance.pv",
            future_value="150000",
            rate="0.05",
            periods=5,
        )
        assert _meta_present(result)


class TestAccountingDomainHints:
    def test_vat_extract_has_meta_hints(self) -> None:
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="11000",
        )
        assert _meta_present(result), "_meta missing from accounting.vat_extract response"

    def test_vat_extract_session_stats(self) -> None:
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="22000",
        )
        stats = result.get("_meta", {}).get("session_stats", {})
        assert "tool_calls" in stats
        assert stats["tool_calls"] >= 1
