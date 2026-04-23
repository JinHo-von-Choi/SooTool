"""Tests for SessionStore / InMemoryStore."""
from __future__ import annotations

import time

from sootool.skill_guide.session_state import (
    _IDLE_TIMEOUT_S,
    _MAX_HISTORY,
    InMemoryStore,
    SessionStore,
    ToolCall,
)


class TestInMemoryStore:
    def _make_store(self) -> InMemoryStore:
        return InMemoryStore()

    def test_implements_protocol(self) -> None:
        store = self._make_store()
        assert isinstance(store, SessionStore)

    def test_record_and_recent(self) -> None:
        store = self._make_store()
        call = ToolCall(tool="core.add")
        store.record("s1", call)
        recent = store.recent("s1")
        assert len(recent) == 1
        assert recent[0].tool == "core.add"

    def test_max_history_20(self) -> None:
        store = self._make_store()
        for i in range(25):
            store.record("s1", ToolCall(tool=f"core.add_{i}"))
        assert len(store.recent("s1")) == _MAX_HISTORY

    def test_oldest_entry_dropped(self) -> None:
        store = self._make_store()
        for i in range(_MAX_HISTORY + 5):
            store.record("s1", ToolCall(tool=f"tool_{i}"))
        recent = store.recent("s1")
        # First 5 tools (0-4) should be dropped
        tools = [c.tool for c in recent]
        assert "tool_0" not in tools
        assert f"tool_{_MAX_HISTORY + 4}" in tools

    def test_session_isolation(self) -> None:
        store = self._make_store()
        store.record("s1", ToolCall(tool="core.add"))
        store.record("s2", ToolCall(tool="core.mul"))
        assert store.recent("s1")[0].tool == "core.add"
        assert store.recent("s2")[0].tool == "core.mul"

    def test_empty_session_returns_empty(self) -> None:
        store = self._make_store()
        assert store.recent("nonexistent") == []

    def test_stats_empty(self) -> None:
        store = self._make_store()
        stats = store.stats("nonexistent")
        assert stats["tool_calls"] == 0
        assert stats["unique_tools"] == 0

    def test_stats_count(self) -> None:
        store = self._make_store()
        store.record("s1", ToolCall(tool="core.add"))
        store.record("s1", ToolCall(tool="core.add"))
        store.record("s1", ToolCall(tool="core.mul"))
        stats = store.stats("s1")
        assert stats["tool_calls"] == 3
        assert stats["unique_tools"] == 2

    def test_gc_removes_idle_sessions(self) -> None:
        store = self._make_store()
        store.record("s_old", ToolCall(tool="core.add"))

        # Manually set last_active to past the timeout
        with store._lock:
            store._sessions["s_old"].last_active = time.monotonic() - _IDLE_TIMEOUT_S - 1

        # Trigger GC by adding a new session
        store.record("s_new", ToolCall(tool="core.mul"))

        assert store.session_count() == 1
        assert store.recent("s_old") == []

    def test_concurrent_sessions_do_not_interfere(self) -> None:
        import threading

        store = self._make_store()
        errors: list[str] = []

        def worker(sid: str) -> None:
            try:
                for _ in range(10):
                    store.record(sid, ToolCall(tool="core.add"))
                assert len(store.recent(sid)) <= _MAX_HISTORY
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(f"s{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
