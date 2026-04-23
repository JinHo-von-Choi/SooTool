"""Tests for _meta.hints generation rules (6 rules)."""
from __future__ import annotations

import datetime
from typing import Any

from sootool.skill_guide.hints import generate_hints, inject_meta
from sootool.skill_guide.session_state import InMemoryStore, ToolCall


def _store_with_calls(calls: list[ToolCall]) -> tuple[InMemoryStore, str]:
    store = InMemoryStore()
    sid = "test-session"
    for call in calls:
        store.record(sid, call)
    return store, sid


def _signal_names(hints: list[dict[str, Any]]) -> list[str]:
    return [h["signal"] for h in hints]


class TestRule1TaxWithoutFullTrace:
    """tax.* call + trace_level != full -> audit warning."""

    def test_tax_summary_trace_triggers(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="tax.kr_income", trace_level="summary")
        hints = generate_hints(store, sid, call)
        assert "tax_without_full_trace" in _signal_names(hints)

    def test_tax_full_trace_no_trigger(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="tax.kr_income", trace_level="full")
        hints = generate_hints(store, sid, call)
        assert "tax_without_full_trace" not in _signal_names(hints)

    def test_realestate_triggers(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="realestate.kr_acquisition_tax", trace_level="none")
        hints = generate_hints(store, sid, call)
        assert "tax_without_full_trace" in _signal_names(hints)

    def test_non_tax_domain_no_trigger(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="finance.npv", trace_level="summary")
        hints = generate_hints(store, sid, call)
        assert "tax_without_full_trace" not in _signal_names(hints)


class TestRule2RepeatedCoreArithmetic:
    """core arithmetic 3+ consecutive -> suggest core.batch."""

    def test_three_consecutive_triggers(self) -> None:
        prev = [
            ToolCall(tool="core.add"),
            ToolCall(tool="core.add"),
        ]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="core.mul")
        hints = generate_hints(store, sid, call)
        assert "repeated_core_arithmetic" in _signal_names(hints)

    def test_two_consecutive_no_trigger(self) -> None:
        prev = [ToolCall(tool="core.add")]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="core.sub")
        hints = generate_hints(store, sid, call)
        assert "repeated_core_arithmetic" not in _signal_names(hints)

    def test_broken_chain_no_trigger(self) -> None:
        prev = [
            ToolCall(tool="core.add"),
            ToolCall(tool="finance.npv"),  # breaks the chain
            ToolCall(tool="core.add"),
        ]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="core.mul")
        # Only 2 consecutive at tail (last core.add + current core.mul)
        hints = generate_hints(store, sid, call)
        assert "repeated_core_arithmetic" not in _signal_names(hints)


class TestRule3StalePolicyYear:
    """policy year older than current year -> refresh warning."""

    def test_old_year_triggers(self) -> None:
        store, sid = _store_with_calls([])
        old_year = datetime.date.today().year - 2
        call = ToolCall(tool="tax.kr_income", policy_year=old_year)
        hints = generate_hints(store, sid, call)
        assert "stale_policy_year" in _signal_names(hints)

    def test_current_year_no_trigger(self) -> None:
        store, sid = _store_with_calls([])
        current_year = datetime.date.today().year
        call = ToolCall(tool="tax.kr_income", policy_year=current_year)
        hints = generate_hints(store, sid, call)
        assert "stale_policy_year" not in _signal_names(hints)

    def test_no_policy_year_no_trigger(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="tax.kr_income", policy_year=None)
        hints = generate_hints(store, sid, call)
        assert "stale_policy_year" not in _signal_names(hints)


class TestRule4TraceTruncated:
    """trace truncated -> payload limit hint."""

    def test_truncated_triggers(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="core.batch", truncated=True)
        hints = generate_hints(store, sid, call)
        assert "trace_truncated" in _signal_names(hints)

    def test_not_truncated_no_trigger(self) -> None:
        store, sid = _store_with_calls([])
        call = ToolCall(tool="core.batch", truncated=False)
        hints = generate_hints(store, sid, call)
        assert "trace_truncated" not in _signal_names(hints)


class TestRule5ManualChain:
    """3+ non-batch/pipeline calls in recent window -> suggest core.pipeline."""

    def test_three_non_pipeline_calls_triggers(self) -> None:
        prev = [
            ToolCall(tool="core.add"),
            ToolCall(tool="finance.npv"),
        ]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="accounting.vat_extract")
        hints = generate_hints(store, sid, call)
        assert "manual_chain_detected" in _signal_names(hints)

    def test_pipeline_in_window_suppresses(self) -> None:
        prev = [
            ToolCall(tool="core.add"),
            ToolCall(tool="core.pipeline"),
            ToolCall(tool="finance.npv"),
        ]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="accounting.vat_extract")
        hints = generate_hints(store, sid, call)
        assert "manual_chain_detected" not in _signal_names(hints)


class TestRule6ExcessiveSingleCalls:
    """20+ single calls without core.batch -> round-trip warning."""

    def test_twenty_calls_triggers(self) -> None:
        prev = [ToolCall(tool="core.add") for _ in range(19)]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="core.add")
        hints = generate_hints(store, sid, call)
        assert "excessive_single_calls" in _signal_names(hints)

    def test_nineteen_calls_no_trigger(self) -> None:
        prev = [ToolCall(tool="core.add") for _ in range(18)]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="core.add")
        hints = generate_hints(store, sid, call)
        assert "excessive_single_calls" not in _signal_names(hints)

    def test_batch_calls_not_counted(self) -> None:
        prev = [ToolCall(tool="core.batch") for _ in range(25)]
        store, sid = _store_with_calls(prev)
        call = ToolCall(tool="core.batch")
        hints = generate_hints(store, sid, call)
        assert "excessive_single_calls" not in _signal_names(hints)


class TestInjectMeta:
    def test_inject_adds_meta(self) -> None:
        response = {"result": "42", "trace": {"tool": "core.add"}}
        hints: list[dict[str, Any]] = [{"signal": "test", "suggestion": "do something", "recommended_tool": None}]
        stats: dict[str, Any] = {"tool_calls": 1, "unique_tools": 1}
        result = inject_meta(response, hints, stats)
        assert "_meta" in result
        assert result["_meta"]["hints"] == hints
        assert result["_meta"]["session_stats"] == stats

    def test_inject_does_not_mutate_original(self) -> None:
        response = {"result": "42"}
        original_keys = set(response.keys())
        inject_meta(response, [], {})
        assert set(response.keys()) == original_keys

    def test_result_and_trace_unchanged(self) -> None:
        response = {"result": "42", "trace": {"tool": "core.add", "output": "42"}}
        result = inject_meta(response, [], {"tool_calls": 0, "unique_tools": 0})
        assert result["result"] == "42"
        assert result["trace"]["output"] == "42"
