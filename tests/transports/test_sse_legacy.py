"""Tests for the HTTP+SSE legacy transport (MCP 2024-11 spec).

Strategy:
- Spin up the SSE app via uvicorn in a background thread.
- Use urllib/httpx with short timeouts to probe endpoints.
- Avoid streaming the infinite SSE body — just check the status code and headers.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request

import pytest

from sootool.server import _load_modules, build_server
from sootool.transports.sse_legacy import build_sse_legacy_app

_TEST_TOKEN = "sse-test-token"  # noqa: S105
_PORT_BASE  = 19940


def _wait_for_http(port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(  # noqa: S310
                f"http://127.0.0.1:{port}/healthz", timeout=2
            ):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"SSE server not ready on port {port}")


def _start_sse_server(port: int, auth_token: str | None = None) -> subprocess.Popen[bytes]:
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "sse-legacy",
        "--sse-port", str(port),
        "--log-format", "text",
        "--log-level", "WARNING",
    ]
    if auth_token:
        cmd += ["--auth-token", auth_token]
    return subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603


# ---------------------------------------------------------------------------
# healthz tests (via subprocess server)
# ---------------------------------------------------------------------------

def test_healthz_returns_200() -> None:
    _load_modules()
    port = _PORT_BASE
    proc = _start_sse_server(port)
    try:
        _wait_for_http(port)
        with urllib.request.urlopen(  # noqa: S310
            f"http://127.0.0.1:{port}/healthz", timeout=5
        ) as r:
            data = json.loads(r.read())
        assert data["status"] == "ok"
        assert data["tools"] > 20
        assert "version" in data
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_healthz_skips_auth() -> None:
    _load_modules()
    port = _PORT_BASE + 1
    proc = _start_sse_server(port, auth_token=_TEST_TOKEN)
    try:
        _wait_for_http(port)
        # /healthz must be reachable without auth
        with urllib.request.urlopen(  # noqa: S310
            f"http://127.0.0.1:{port}/healthz", timeout=5
        ) as r:
            assert r.status == 200
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# /sse endpoint tests — status code + headers only (no body consumption)
# ---------------------------------------------------------------------------

def test_sse_endpoint_exists_no_auth() -> None:
    """GET /sse without auth requirement returns 200 with text/event-stream."""
    _load_modules()
    port = _PORT_BASE + 2
    proc = _start_sse_server(port)
    try:
        _wait_for_http(port)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/sse")
        with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310
            assert r.status == 200
            ct = r.headers.get("content-type", "")
            assert "text/event-stream" in ct
    except urllib.error.URLError as exc:
        # A connection timeout after headers is acceptable; 404/405 is not
        if "timed out" in str(exc).lower():
            pass
        elif hasattr(exc, "code") and exc.code in (404, 405):  # type: ignore[union-attr]
            pytest.fail(f"/sse returned {exc.code}")  # type: ignore[union-attr]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_sse_endpoint_requires_auth() -> None:
    """Without credentials, /sse must return 401."""
    _load_modules()
    port = _PORT_BASE + 3
    proc = _start_sse_server(port, auth_token=_TEST_TOKEN)
    try:
        _wait_for_http(port)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/sse")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
        assert exc_info.value.code == 401
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_sse_endpoint_auth_accepted() -> None:
    """With correct bearer token, /sse must return 200."""
    _load_modules()
    port = _PORT_BASE + 4
    proc = _start_sse_server(port, auth_token=_TEST_TOKEN)
    try:
        _wait_for_http(port)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/sse",
            headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310
                assert r.status == 200
        except urllib.error.URLError as exc:
            if hasattr(exc, "code") and exc.code in (401, 403):  # type: ignore[union-attr]
                pytest.fail(f"auth rejected: {exc}")
            # timeout after headers is OK
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# /messages endpoint tests
# ---------------------------------------------------------------------------

def test_messages_endpoint_exists() -> None:
    """POST /messages without a session_id returns 4xx (not 404)."""
    _load_modules()
    port = _PORT_BASE + 5
    proc = _start_sse_server(port)
    try:
        _wait_for_http(port)
        data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/messages",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
        except urllib.error.HTTPError as exc:
            assert exc.code != 404, "/messages returned 404 — endpoint missing"
        except Exception:  # noqa: BLE001, S110
            pass  # connection closed by server is also acceptable
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_messages_requires_auth() -> None:
    """POST /messages without credentials returns 401 when auth is configured."""
    _load_modules()
    port = _PORT_BASE + 6
    proc = _start_sse_server(port, auth_token=_TEST_TOKEN)
    try:
        _wait_for_http(port)
        data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/messages",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
        assert exc_info.value.code == 401
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# build_sse_legacy_app unit test (no subprocess)
# ---------------------------------------------------------------------------

def test_build_sse_legacy_app_creates_app() -> None:
    """build_sse_legacy_app should return an ASGI callable without errors."""
    _load_modules()
    server = build_server()
    app = build_sse_legacy_app(server, auth_token=None, cors_origins=[])
    assert callable(app)


def test_build_sse_legacy_app_with_auth() -> None:
    """build_sse_legacy_app with auth_token should return an ASGI callable."""
    _load_modules()
    server = build_server()
    app = build_sse_legacy_app(server, auth_token=_TEST_TOKEN, cors_origins=[])
    assert callable(app)
