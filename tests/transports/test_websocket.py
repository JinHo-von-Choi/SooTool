"""Tests for the WebSocket transport."""
from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sootool.server import _load_modules, build_server
from sootool.transports.websocket import build_ws_app

_TEST_TOKEN = "ws-test-token"  # noqa: S105


@pytest.fixture(scope="module")
def ws_client_authed() -> TestClient:
    _load_modules()
    server = build_server()
    app = build_ws_app(server, auth_token=_TEST_TOKEN, cors_origins=[])
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def ws_client_no_auth() -> TestClient:
    _load_modules()
    server = build_server()
    app = build_ws_app(server, auth_token=None, cors_origins=[])
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def ws_client_cors() -> TestClient:
    _load_modules()
    server = build_server()
    app = build_ws_app(
        server,
        auth_token=None,
        cors_origins=["https://allowed.example.com"],
    )
    return TestClient(app, raise_server_exceptions=False)


# --- healthz ---

def test_healthz_returns_200(ws_client_no_auth: TestClient) -> None:
    resp = ws_client_no_auth.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["tools"] > 20


# --- WebSocket upgrade ---

def test_ws_upgrade_no_auth(ws_client_no_auth: TestClient) -> None:
    """Without token requirement, upgrade succeeds."""
    with ws_client_no_auth.websocket_connect("/ws") as ws:
        # Connection accepted; server sends no initial message — just verify open
        ws.close()


def test_ws_upgrade_missing_token_rejected(ws_client_authed: TestClient) -> None:
    """Without credentials, the server must close the connection."""
    with pytest.raises((WebSocketDisconnect, Exception)):
        with ws_client_authed.websocket_connect("/ws") as ws:
            # Drain any initial frame before detecting close
            ws.receive_text()


def test_ws_upgrade_wrong_token_rejected(ws_client_authed: TestClient) -> None:
    with pytest.raises((WebSocketDisconnect, Exception)):
        with ws_client_authed.websocket_connect(
            "/ws",
            headers={"Authorization": "Bearer wrongtoken"},
        ) as ws:
            ws.receive_text()


def test_ws_upgrade_correct_token_accepted(ws_client_authed: TestClient) -> None:
    with ws_client_authed.websocket_connect(
        "/ws",
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    ) as ws:
        ws.close()


# --- Origin validation ---

def test_ws_disallowed_origin_rejected(ws_client_cors: TestClient) -> None:
    """Origin not in allow-list must be rejected."""
    with pytest.raises((WebSocketDisconnect, Exception)):
        with ws_client_cors.websocket_connect(
            "/ws",
            headers={"Origin": "https://evil.example.com"},
        ) as ws:
            ws.receive_text()


def test_ws_allowed_origin_accepted(ws_client_cors: TestClient) -> None:
    with ws_client_cors.websocket_connect(
        "/ws",
        headers={"Origin": "https://allowed.example.com"},
    ) as ws:
        ws.close()


# --- JSON-RPC tool roundtrip ---

def test_ws_tool_roundtrip_initialize(ws_client_no_auth: TestClient) -> None:
    """Send an initialize request; server should respond with capabilities."""
    with ws_client_no_auth.websocket_connect("/ws") as ws:
        ws.send_text(
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test", "version": "0.1"},
                    "capabilities": {},
                },
            })
        )
        raw = ws.receive_text()
        msg = json.loads(raw)
        # Response should be for id=1
        assert msg.get("id") == 1
        assert "result" in msg
        ws.close()
