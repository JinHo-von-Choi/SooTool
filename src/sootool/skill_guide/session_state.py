"""Session state management for _meta.hints generation.

Implements SessionStore protocol + InMemoryStore.
Session scope: stdio process lifetime, HTTP mcp-session-id, WebSocket connection.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Protocol, runtime_checkable

_MAX_HISTORY = 20
_IDLE_TIMEOUT_S = 1800  # 30 minutes


class ToolCall:
    """Record of a single tool invocation within a session."""

    __slots__ = ("tool", "timestamp", "trace_level", "truncated", "policy_year", "domain")

    def __init__(
        self,
        tool: str,
        trace_level: str = "summary",
        truncated: bool = False,
        policy_year: int | None = None,
    ) -> None:
        self.tool        = tool
        self.timestamp   = time.monotonic()
        self.trace_level = trace_level
        self.truncated   = truncated
        self.policy_year = policy_year
        self.domain      = tool.split(".")[0] if "." in tool else tool


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for session-level call history tracking."""

    def record(self, session_id: str, call: ToolCall) -> None:
        """Record a tool call for the given session."""
        ...

    def recent(self, session_id: str) -> list[ToolCall]:
        """Return up to the last MAX_HISTORY calls for the session."""
        ...

    def stats(self, session_id: str) -> dict[str, Any]:
        """Return aggregate statistics for the session."""
        ...


class _SessionData:
    __slots__ = ("history", "last_active")

    def __init__(self) -> None:
        self.history: deque[ToolCall] = deque(maxlen=_MAX_HISTORY)
        self.last_active: float       = time.monotonic()


class InMemoryStore:
    """Thread-safe in-memory session store.

    - Keeps last _MAX_HISTORY calls per session.
    - GC sessions idle for _IDLE_TIMEOUT_S seconds.
    - Each session is isolated; cross-session sharing is not permitted.
    """

    def __init__(self) -> None:
        import threading
        self._sessions: dict[str, _SessionData] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # SessionStore interface
    # ------------------------------------------------------------------

    def record(self, session_id: str, call: ToolCall) -> None:
        with self._lock:
            self._gc_unsafe()
            if session_id not in self._sessions:
                self._sessions[session_id] = _SessionData()
            sd = self._sessions[session_id]
            sd.history.append(call)
            sd.last_active = time.monotonic()

    def recent(self, session_id: str) -> list[ToolCall]:
        with self._lock:
            if session_id not in self._sessions:
                return []
            return list(self._sessions[session_id].history)

    def stats(self, session_id: str) -> dict[str, Any]:
        calls = self.recent(session_id)
        if not calls:
            return {"tool_calls": 0, "unique_tools": 0}
        unique_tools = len({c.tool for c in calls})
        return {
            "tool_calls":   len(calls),
            "unique_tools": unique_tools,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _gc_unsafe(self) -> None:
        """Remove idle sessions. Must be called with self._lock held."""
        now = time.monotonic()
        dead = [sid for sid, sd in self._sessions.items() if now - sd.last_active > _IDLE_TIMEOUT_S]
        for sid in dead:
            del self._sessions[sid]

    def session_count(self) -> int:
        """Number of active sessions (for diagnostics)."""
        with self._lock:
            self._gc_unsafe()
            return len(self._sessions)


# Module-level singleton — shared within a single process.
# HTTP/WebSocket sessions must pass distinct session_id values.
STORE: InMemoryStore = InMemoryStore()
