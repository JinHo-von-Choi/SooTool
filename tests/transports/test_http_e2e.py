"""Streamable HTTP 종단 시험: 인증 범위, 무상태, 로케일, 쓰기 도구 노출."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx2
import pytest
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

from sootool.server import _load_modules, build_server
from sootool.transports.http import build_http_app

_READ_TOKEN  = "read-token"   # noqa: S105
_ADMIN_TOKEN = "admin-token"  # noqa: S105


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    _load_modules()


async def _call(base_url: str, tool: str, arguments: dict[str, Any], *, token: str | None = None,
                headers: dict[str, str] | None = None) -> Any:
    merged = dict(headers or {})
    if token:
        merged["Authorization"] = f"Bearer {token}"
    http_client = httpx2.AsyncClient(headers=merged)
    async with Client(streamable_http_client(f"{base_url}/mcp", http_client=http_client)) as client:
        return await client.call_tool(tool, arguments)


async def _list(base_url: str, *, token: str | None = None) -> set[str]:
    http_client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"} if token else {})
    async with Client(streamable_http_client(f"{base_url}/mcp", http_client=http_client)) as client:
        return {t.name for t in (await client.list_tools()).tools}


def test_authenticated_tool_call_succeeds(serve_app) -> None:
    app = build_http_app(build_server(expose_writes=False), _READ_TOKEN, [])
    with serve_app(app) as base_url:
        result = asyncio.run(_call(base_url, "core.add", {"operands": ["1", "2"]}, token=_READ_TOKEN))
    assert result.structured_content["result"] == "3"


def test_http_responses_are_stateless(serve_app) -> None:
    app = build_http_app(build_server(expose_writes=False), None, [])
    with serve_app(app) as base_url:
        first  = asyncio.run(_call(base_url, "core.add", {"operands": ["1", "2"]}))
        second = asyncio.run(_call(base_url, "core.add", {"operands": ["1", "2"]}))
    for result in (first, second):
        assert "session_stats" not in result.structured_content["_meta"]
        assert "integrity" in result.structured_content["_meta"]


def test_accept_language_reaches_the_tool(serve_app) -> None:
    app = build_http_app(build_server(expose_writes=False), None, [])
    with serve_app(app) as base_url:
        english = asyncio.run(_call(base_url, "sootool.skill_guide", {"section": "triggers"},
                                    headers={"Accept-Language": "en-US,en;q=0.9"}))
        default = asyncio.run(_call(base_url, "sootool.skill_guide", {"section": "triggers"}))
        explicit = asyncio.run(_call(base_url, "sootool.skill_guide", {"section": "triggers", "lang": "ko"},
                                     headers={"Accept-Language": "en"}))
    assert english.structured_content["locale"] == "en"
    assert default.structured_content["locale"] == "ko"
    assert explicit.structured_content["locale"] == "ko"


def test_locale_does_not_leak_between_requests(serve_app) -> None:
    app = build_http_app(build_server(expose_writes=False), None, [])
    with serve_app(app) as base_url:
        asyncio.run(_call(base_url, "sootool.skill_guide", {"section": "triggers"},
                          headers={"Accept-Language": "en"}))
        after = asyncio.run(_call(base_url, "sootool.skill_guide", {"section": "triggers"}))
    assert after.structured_content["locale"] == "ko"


def test_remote_server_without_writes_does_not_advertise_policy_write_tools(serve_app) -> None:
    app = build_http_app(build_server(expose_writes=False), None, [])
    with serve_app(app) as base_url:
        names = asyncio.run(_list(base_url))
    assert "core.add" in names
    assert "sootool.policy_activate" not in names
    assert "sootool.policy_get" in names


def test_policy_write_requires_admin_scope_token(serve_app, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    args = {"domain": "tax", "name": "kr_income", "year": 2026}
    app = build_http_app(build_server(expose_writes=True), _READ_TOKEN, [], admin_token=_ADMIN_TOKEN)
    with serve_app(app) as base_url:
        with_read  = asyncio.run(_call(base_url, "sootool.policy_rollback", args, token=_READ_TOKEN))
        with_admin = asyncio.run(_call(base_url, "sootool.policy_rollback", args, token=_ADMIN_TOKEN))
    assert with_read.structured_content["error"] == "admin_required"
    assert "error" not in with_admin.structured_content


def test_missing_and_wrong_tokens_are_rejected(serve_app) -> None:
    import urllib.error
    import urllib.request

    app = build_http_app(build_server(expose_writes=False), _READ_TOKEN, [], admin_token=_ADMIN_TOKEN)
    with serve_app(app) as base_url:
        for header in (None, "Bearer nope"):
            request = urllib.request.Request(f"{base_url}/mcp", data=b"{}", method="POST")  # noqa: S310
            if header:
                request.add_header("Authorization", header)
            with pytest.raises(urllib.error.HTTPError) as info:
                urllib.request.urlopen(request, timeout=5)  # noqa: S310
            assert info.value.code == 401
        with urllib.request.urlopen(f"{base_url}/healthz", timeout=5) as ok:  # noqa: S310
            assert ok.status == 200


def test_error_contract_over_http(serve_app) -> None:
    app = build_http_app(build_server(expose_writes=False), None, [])
    with serve_app(app) as base_url:
        result = asyncio.run(_call(base_url, "probability.factorial", {"n": 10**6}))
    assert result.is_error
    error = result.structured_content["error"]
    assert error["code"] == "input_limit"
    assert error["details"]["limit"] > 0
