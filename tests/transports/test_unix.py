"""Tests for the Unix Domain Socket transport (Streamable HTTP over UDS)."""
from __future__ import annotations

import asyncio
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


async def _mcp_call(sock_path: str, tool: str, arguments: dict) -> object:  # type: ignore[type-arg]
    import httpx2
    from mcp.client import Client
    from mcp.client.streamable_http import streamable_http_client

    http_client = httpx2.AsyncClient(transport=httpx2.AsyncHTTPTransport(uds=sock_path))
    async with Client(streamable_http_client("http://localhost/mcp", http_client=http_client)) as client:
        return await client.call_tool(tool, arguments)


def test_mcp_tool_call_roundtrip_over_socket() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "rpc.sock")
        _start_transport(sock_path)
        _wait_for_socket(sock_path)

        result = asyncio.run(_mcp_call(sock_path, "core.add", {"operands": ["1.5", "2.5"]}))
        assert result.structured_content["result"] == "4.0"  # type: ignore[attr-defined]
        assert "integrity" in result.structured_content["_meta"]  # type: ignore[attr-defined]


def test_multiple_independent_clients() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "multi.sock")
        _start_transport(sock_path)
        _wait_for_socket(sock_path)

        for i in range(3):
            result = asyncio.run(_mcp_call(sock_path, "core.add", {"operands": [str(i), "1"]}))
            assert result.structured_content["result"] == str(i + 1)  # type: ignore[attr-defined]


def test_requests_over_socket_are_stateless() -> None:
    """네트워크 계열 요청은 호출 이력을 쓰지 않으므로 session_stats 가 없다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "stateless.sock")
        _start_transport(sock_path)
        _wait_for_socket(sock_path)

        result = asyncio.run(_mcp_call(sock_path, "core.add", {"operands": ["1", "2"]}))
        assert "session_stats" not in result.structured_content["_meta"]  # type: ignore[attr-defined]


def test_non_socket_file_at_path_is_refused() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "regular.file")
        Path(sock_path).write_text("not a socket", encoding="utf-8")

        _load_modules()
        transport = UnixTransport(server=build_server(), socket_path=sock_path)
        with pytest.raises(RuntimeError, match="not a Unix socket"):
            asyncio.run(transport.start_async())
        assert Path(sock_path).read_text(encoding="utf-8") == "not a socket"


def test_socket_is_never_group_or_world_accessible_while_binding() -> None:
    """바인드 시점부터 요청한 권한으로 생성되어 chmod 이전 틈이 없다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = Path(tmpdir) / "bind.sock"
        _load_modules()
        transport = UnixTransport(server=build_server(), socket_path=str(sock_path), socket_mode=0o600)
        previous = os.umask(0o000)
        try:
            sock = transport._bind_socket(sock_path)
        finally:
            os.umask(previous)
        try:
            assert stat.S_IMODE(sock_path.stat().st_mode) == 0o600
        finally:
            sock.close()


def test_default_socket_path_lives_in_private_runtime_directory(monkeypatch, tmp_path) -> None:
    from sootool.transports.unix import _effective_socket_path

    monkeypatch.delenv("SOOTOOL_SOCKET_PATH", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    path = Path(_effective_socket_path(None))
    assert path == tmp_path / "sootool" / "sootool.sock"
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
