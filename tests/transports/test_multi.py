"""Integration test: stdio + http simultaneous startup."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request

_PORT = 19997
_TOKEN = "multi-test-token"  # noqa: S105
_TIMEOUT = 20


def _wait_for_http(port: int, timeout: float = _TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2):  # noqa: S310
                return
        except Exception:
            time.sleep(0.25)
    raise TimeoutError(f"HTTP transport not ready within {timeout}s")


def test_stdio_http_simultaneous_startup() -> None:
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "stdio,http",
        "--http-port", str(_PORT),
        "--auth-token", _TOKEN,
        "--log-format", "text",
        "--log-level", "WARNING",
    ]
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_http(_PORT)

        with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/healthz", timeout=5) as r:  # noqa: S310
            import json
            data = json.loads(r.read())
        assert data["status"] == "ok"
        assert data["tools"] > 20
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_http_only_binds_and_responds() -> None:
    port = _PORT + 1
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "http",
        "--http-port", str(port),
        "--auth-token", _TOKEN,
        "--log-format", "text",
    ]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603
    try:
        _wait_for_http(port)

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/healthz",
        )
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            import json
            data = json.loads(r.read())
        assert data["status"] == "ok"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_host_0000_without_token_exits_nonzero() -> None:
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "http",
        "--host", "0.0.0.0",  # noqa: S104
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=10)  # noqa: S603
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "auth" in stderr.lower() or "token" in stderr.lower()


def _wait_for_socket(sock_path: str, timeout: float = _TIMEOUT) -> None:
    import socket as _socket
    from pathlib import Path

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if Path(sock_path).exists():
            try:
                with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(sock_path)
                    return
            except OSError:
                pass
        time.sleep(0.25)
    raise TimeoutError(f"Unix socket not ready within {timeout}s")


def test_sse_legacy_startup() -> None:
    """SSE legacy transport binds and healthz responds."""
    port = _PORT + 10
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "sse-legacy",
        "--sse-port", str(port),
        "--auth-token", _TOKEN,
        "--log-format", "text",
    ]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603
    try:
        _wait_for_http(port)
        req = urllib.request.Request(f"http://127.0.0.1:{port}/healthz")
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            import json
            data = json.loads(r.read())
        assert data["status"] == "ok"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_unix_socket_startup() -> None:
    """Unix socket transport creates the socket file and serves MCP over HTTP."""
    import asyncio
    import tempfile

    import httpx2
    from mcp.client import Client
    from mcp.client.streamable_http import streamable_http_client

    async def _roundtrip(sock_path: str) -> object:
        http_client = httpx2.AsyncClient(transport=httpx2.AsyncHTTPTransport(uds=sock_path))
        async with Client(streamable_http_client("http://localhost/mcp", http_client=http_client)) as client:
            return await client.call_tool("core.add", {"operands": ["1", "2"]})

    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        sock_path = os.path.join(tmpdir, "multi_test.sock")
        cmd = [
            sys.executable, "-m", "sootool",
            "--transport", "unix",
            "--socket", sock_path,
            "--log-format", "text",
        ]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603
        try:
            _wait_for_socket(sock_path)
            result = asyncio.run(_roundtrip(sock_path))
            assert result.structured_content["result"] == "3"  # type: ignore[attr-defined]
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def test_host_0000_sse_legacy_without_token_exits_nonzero() -> None:
    """SSE legacy transport with 0.0.0.0 and no token must refuse startup."""
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "sse-legacy",
        "--host", "0.0.0.0",  # noqa: S104
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=10)  # noqa: S603
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "auth" in stderr.lower() or "token" in stderr.lower()


def test_websocket_transport_is_rejected_with_migration_message() -> None:
    cmd = [sys.executable, "-m", "sootool", "--transport", "websocket"]
    result = subprocess.run(cmd, capture_output=True, timeout=20)  # noqa: S603
    assert result.returncode != 0
    stderr = result.stderr.decode().lower()
    assert "websocket" in stderr and "removed" in stderr and "http" in stderr


def test_remote_admin_requires_admin_token() -> None:
    cmd = [sys.executable, "-m", "sootool", "--transport", "http", "--remote-admin"]
    env = {k: v for k, v in __import__("os").environ.items() if k != "SOOTOOL_ADMIN_TOKEN"}
    result = subprocess.run(cmd, capture_output=True, timeout=20, env=env)  # noqa: S603
    assert result.returncode != 0
    assert "admin token" in result.stderr.decode().lower()


def test_remote_admin_rejected_without_network_transport() -> None:
    cmd = [sys.executable, "-m", "sootool", "--transport", "stdio", "--remote-admin", "--admin-token", "t"]
    result = subprocess.run(cmd, capture_output=True, timeout=20, input=b"")  # noqa: S603
    assert result.returncode != 0
    assert "network transports" in result.stderr.decode().lower()


def test_four_transport_simultaneous_startup() -> None:
    """stdio + http + sse-legacy + unix all start together."""
    import os
    import tempfile
    from pathlib import Path

    http_port = _PORT + 20
    sse_port  = _PORT + 21
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "four.sock")
        cmd = [
            sys.executable, "-m", "sootool",
            "--transport", "stdio,http,sse-legacy,unix",
            "--http-port", str(http_port),
            "--sse-port",  str(sse_port),
            "--socket", sock_path,
            "--auth-token", _TOKEN,
            "--log-format", "text",
            "--log-level", "WARNING",
        ]
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            _wait_for_http(http_port)
            _wait_for_http(sse_port)
            _wait_for_socket(sock_path)
            assert Path(sock_path).exists()

            import json
            for port in (http_port, sse_port):
                with urllib.request.urlopen(  # noqa: S310
                    f"http://127.0.0.1:{port}/healthz", timeout=5
                ) as r:
                    data = json.loads(r.read())
                assert data["status"] == "ok"
                assert data["tools"] > 20
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
