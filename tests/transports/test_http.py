"""Tests for the HTTP transport ASGI app: healthz, auth, and MCP tool roundtrip."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sootool.server import _load_modules, build_server
from sootool.transports.http import build_http_app

_TEST_TOKEN = "test-token"  # noqa: S105


@pytest.fixture(scope="module")
def http_client_authed() -> TestClient:
    _load_modules()
    server = build_server()
    app = build_http_app(server, auth_token=_TEST_TOKEN, cors_origins=[])
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def http_client_no_auth() -> TestClient:
    _load_modules()
    server = build_server()
    app = build_http_app(server, auth_token=None, cors_origins=[])
    return TestClient(app, raise_server_exceptions=False)


def test_healthz_returns_200(http_client_no_auth: TestClient) -> None:
    resp = http_client_no_auth.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["tools"], int)
    assert data["tools"] > 20
    assert "version" in data
    assert "uptime_s" in data


def test_healthz_skips_auth(http_client_authed: TestClient) -> None:
    resp = http_client_authed.get("/healthz")
    assert resp.status_code == 200


def test_auth_missing_token_returns_401(http_client_authed: TestClient) -> None:
    resp = http_client_authed.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp.status_code == 401


def test_auth_wrong_token_returns_401(http_client_authed: TestClient) -> None:
    resp = http_client_authed.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert resp.status_code == 401


def test_auth_correct_token_accepted(http_client_authed: TestClient) -> None:
    resp = http_client_authed.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    )
    assert resp.status_code != 401


def test_no_auth_configured_allows_request(http_client_no_auth: TestClient) -> None:
    resp = http_client_no_auth.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert resp.status_code != 401
