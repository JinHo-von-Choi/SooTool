"""
MCP HTTP+SSE (deprecated transport) integration smoke test for SooTool.

Starts the server with --transport sse-legacy and a Bearer token, connects with the official
MCP Python SDK SSE client, and verifies the tool calls and the error contract.

Run:
    uv run python scripts/mcp_smoke_sse.py
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from _smoke_common import http_ready, run_checks, stop, wait_until
from mcp.client import Client
from mcp.client.sse import sse_client

_PORT  = 19998
_TOKEN = "smoke-test-token"  # noqa: S105
_URL   = f"http://127.0.0.1:{_PORT}/sse"


async def main() -> None:
    env = {**os.environ, "SOOTOOL_AUTH_TOKEN": _TOKEN}
    cmd = [
        sys.executable, "-m", "sootool", "--transport", "sse-legacy",
        "--sse-port", str(_PORT), "--log-format", "text",
    ]
    proc = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)  # noqa: S603
    try:
        wait_until(http_ready(_PORT), proc, "sse server")
        print(f"Server ready on port {_PORT}")
        async with Client(sse_client(_URL, headers={"Authorization": f"Bearer {_TOKEN}"})) as client:
            await run_checks(client)
    finally:
        stop(proc)


if __name__ == "__main__":
    asyncio.run(main())
