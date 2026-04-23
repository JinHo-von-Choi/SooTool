"""Tests for the Unix Domain Socket transport."""
from __future__ import annotations

import asyncio
import json
import os
import socket
import stat
import tempfile
import threading
import time
from pathlib import Path

import pytest

from sootool.server import _load_modules, build_server
from sootool.transports.unix import UnixTransport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send_recv(
    sock_path: str,
    payload: dict,  # type: ignore[type-arg]
    timeout: float = 5.0,
) -> dict:  # type: ignore[type-arg]
    """Send a JSON-RPC message over a Unix socket and read the response."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect(sock_path)
        frame = (json.dumps(payload) + "\n").encode()
        sock.sendall(frame)
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        line = buf.split(b"\n")[0]
        return json.loads(line)  # type: ignore[no-any-return]


def _start_transport(
    sock_path: str,
    socket_mode: int = 0o600,
    force: bool = False,
) -> tuple[threading.Thread, asyncio.AbstractEventLoop]:
    """Start UnixTransport in a background thread, return (thread, loop)."""
    _load_modules()
    server = build_server()
    transport = UnixTransport(
        server=server,
        socket_path=sock_path,
        socket_mode=socket_mode,
        force=force,
    )

    loop = asyncio.new_event_loop()

    def _run() -> None:
        loop.run_until_complete(transport.start_async())

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread, loop


def _wait_for_socket(sock_path: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if Path(sock_path).exists():
            # Also verify we can connect
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(sock_path)
                    return
            except OSError:
                pass
        time.sleep(0.1)
    raise TimeoutError(f"Unix socket not ready within {timeout}s: {sock_path}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_socket_file_created() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "test.sock")
        _start_transport(sock_path)
        _wait_for_socket(sock_path)
        assert Path(sock_path).exists()


def test_socket_mode_0600() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "test.sock")
        _start_transport(sock_path, socket_mode=0o600)
        _wait_for_socket(sock_path)
        mode = stat.S_IMODE(Path(sock_path).stat().st_mode)
        assert mode == 0o600


def test_socket_mode_custom() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "test.sock")
        _start_transport(sock_path, socket_mode=0o660)
        _wait_for_socket(sock_path)
        mode = stat.S_IMODE(Path(sock_path).stat().st_mode)
        assert mode == 0o660


def test_stale_socket_refused() -> None:
    """If socket file already exists and --force-socket is off, startup must raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "stale.sock")

        # Create a dummy socket file to simulate stale socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as dummy:
            dummy.bind(sock_path)
        assert Path(sock_path).exists()

        _load_modules()
        server = build_server()
        transport = UnixTransport(
            server=server,
            socket_path=sock_path,
            socket_mode=0o600,
            force=False,
        )
        with pytest.raises(RuntimeError, match="already exists"):
            asyncio.run(transport.start_async())


def test_stale_socket_force_removes() -> None:
    """--force-socket must remove the stale socket and start successfully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "stale.sock")

        # Create a dummy socket file
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as dummy:
            dummy.bind(sock_path)

        _start_transport(sock_path, force=True)
        _wait_for_socket(sock_path)
        assert Path(sock_path).exists()


def test_json_rpc_roundtrip() -> None:
    """Send initialize request, receive valid JSON-RPC response."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "rpc.sock")
        _start_transport(sock_path)
        _wait_for_socket(sock_path)

        resp = _send_recv(
            sock_path,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test", "version": "0.1"},
                    "capabilities": {},
                },
            },
        )
        assert resp.get("id") == 1
        assert "result" in resp


def test_multiple_connections() -> None:
    """Multiple independent connections should each get valid responses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "multi.sock")
        _start_transport(sock_path)
        _wait_for_socket(sock_path)

        for i in range(3):
            resp = _send_recv(
                sock_path,
                {
                    "jsonrpc": "2.0",
                    "id": i,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "clientInfo": {"name": "test", "version": "0.1"},
                        "capabilities": {},
                    },
                },
            )
            assert resp.get("id") == i
            assert "result" in resp
