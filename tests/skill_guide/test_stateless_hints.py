from __future__ import annotations

from sootool.core.request_context import request_context
from sootool.skill_guide.hints import generate_hints, inject_meta
from sootool.skill_guide.session_state import STORE, InMemoryStore, ToolCall


def _arith(n: int) -> list[ToolCall]:
    return [ToolCall("core.add") for _ in range(n)]


def test_stateless_request_ignores_call_history():
    store = InMemoryStore()
    for call in _arith(5):
        store.record("s", call)
    stateless = generate_hints(store, None, ToolCall("core.add"))
    stateful  = generate_hints(store, "s", ToolCall("core.add"))
    assert "repeated_core_arithmetic" in {h["signal"] for h in stateful}
    assert "repeated_core_arithmetic" not in {h["signal"] for h in stateless}


def test_current_call_rules_still_fire_without_a_session():
    hints = generate_hints(InMemoryStore(), None, ToolCall("tax.kr_income", policy_year=2020))
    signals = {h["signal"] for h in hints}
    assert {"tax_without_full_trace", "stale_policy_year"} <= signals


def test_inject_meta_omits_session_stats_when_none():
    meta = inject_meta({"result": "1"}, [], None)["_meta"]
    assert meta == {"hints": []}
    assert "session_stats" in inject_meta({"result": "1"}, [], {"tool_calls": 1})["_meta"]


def test_stateless_requests_do_not_grow_the_shared_store():
    from sootool import server as S
    from sootool.core.registry import REGISTRY

    S._load_modules()
    before = STORE.session_count()
    with request_context(stateless=True):
        out = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert "session_stats" not in out["_meta"]
    assert STORE.session_count() == before


def test_local_calls_keep_session_stats():
    from sootool import server as S
    from sootool.core.registry import REGISTRY

    S._load_modules()
    assert "session_stats" in REGISTRY.invoke("core.add", operands=["1", "2"])["_meta"]


def test_session_store_has_no_locale_state():
    assert not hasattr(InMemoryStore(), "set_locale")
