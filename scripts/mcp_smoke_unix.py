"""
MCP Unix domain socket integration smoke test for SooTool.

Starts the server with --transport unix, connects with the official MCP Python SDK over
Streamable HTTP on the socket, and verifies the tool calls and the error contract. Also checks
that the socket file is created with owner-only permissions.

Run:
    uv run python scripts/mcp_smoke_unix.py
"""
from __future__ import annotations

import asyncio
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx2
from _smoke_common import check, run_checks, socket_ready, stop, wait_until
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sock = Path(tmp) / "sootool.sock"
        cmd  = [
            sys.executable, "-m", "sootool", "--transport", "unix",
            "--socket", str(sock), "--log-format", "text",
        ]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603
        try:
            wait_until(socket_ready(sock), proc, "unix socket")
            mode = stat.S_IMODE(sock.stat().st_mode)
            check(mode == 0o600, f"socket mode is 0600 (got {oct(mode)})")

            transport   = httpx2.AsyncHTTPTransport(uds=str(sock))
            http_client = httpx2.AsyncClient(transport=transport)
            async with Client(streamable_http_client("http://localhost/mcp", http_client=http_client)) as client:
                await run_checks(client)
        finally:
            stop(proc)


if __name__ == "__main__":
    asyncio.run(main())
