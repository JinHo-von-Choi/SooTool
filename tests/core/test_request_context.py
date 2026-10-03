from __future__ import annotations

import asyncio
import contextvars

import pytest

from sootool.core.request_context import (
    REQUEST_LOCALE,
    REQUEST_SCOPES,
    SCOPE_POLICY_WRITE,
    SCOPE_READ,
    STATELESS_REQUEST,
    has_scope,
    request_context,
)


def test_defaults_are_the_local_trusted_context():
    assert REQUEST_LOCALE.get() is None
    assert STATELESS_REQUEST.get() is False
    assert REQUEST_SCOPES.get() is None


def test_context_values_are_set_inside_and_restored_after():
    with request_context(locale="en", stateless=True, scopes=frozenset({SCOPE_READ})):
        assert REQUEST_LOCALE.get() == "en"
        assert STATELESS_REQUEST.get() is True
        assert REQUEST_SCOPES.get() == frozenset({SCOPE_READ})
    assert REQUEST_LOCALE.get() is None
    assert STATELESS_REQUEST.get() is False
    assert REQUEST_SCOPES.get() is None


def test_values_are_restored_even_when_the_block_raises():
    with pytest.raises(RuntimeError), request_context(locale="en", stateless=True):
        raise RuntimeError("boom")
    assert REQUEST_LOCALE.get() is None
    assert STATELESS_REQUEST.get() is False


def test_nested_contexts_restore_the_outer_values():
    with request_context(locale="en"):
        with request_context(locale="ko"):
            assert REQUEST_LOCALE.get() == "ko"
        assert REQUEST_LOCALE.get() == "en"


def test_has_scope_is_true_for_the_local_context():
    assert has_scope(SCOPE_POLICY_WRITE) is True


def test_has_scope_checks_membership_when_scopes_are_set():
    with request_context(scopes=frozenset({SCOPE_READ})):
        assert has_scope(SCOPE_READ) is True
        assert has_scope(SCOPE_POLICY_WRITE) is False
    with request_context(scopes=frozenset()):
        assert has_scope(SCOPE_READ) is False


def test_concurrent_requests_do_not_see_each_others_values():
    async def request(locale: str, delay: float) -> str | None:
        with request_context(locale=locale, stateless=True):
            await asyncio.sleep(delay)
            return REQUEST_LOCALE.get()

    async def main() -> list[str | None]:
        return await asyncio.gather(request("en", 0.05), request("ko", 0.01))

    assert asyncio.run(main()) == ["en", "ko"]


def test_values_propagate_into_copied_contexts_like_worker_threads():
    with request_context(locale="en", scopes=frozenset({SCOPE_READ})):
        snapshot = contextvars.copy_context()
    assert snapshot.run(REQUEST_LOCALE.get) == "en"
    assert snapshot.run(REQUEST_SCOPES.get) == frozenset({SCOPE_READ})


def test_admin_gate_honors_request_scope(monkeypatch):
    from sootool.policy_mgmt.tools import _is_admin

    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    assert _is_admin() is True
    with request_context(scopes=frozenset({SCOPE_READ})):
        assert _is_admin() is False
    with request_context(scopes=frozenset({SCOPE_READ, SCOPE_POLICY_WRITE})):
        assert _is_admin() is True
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE")
    with request_context(scopes=frozenset({SCOPE_READ, SCOPE_POLICY_WRITE})):
        assert _is_admin() is False
