"""
MCP Streamable HTTP integration smoke test for SooTool.

Starts the server with --transport http and a Bearer token, connects with the official MCP
Python SDK HTTP client, and verifies the tool calls and the error contract. Also checks that
requests without the token are rejected and that /healthz is open.

Run:
    uv run python scripts/mcp_smoke_http.py
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import urllib.error
import urllib.request

import httpx2
from _smoke_common import check, http_ready, run_checks, stop, wait_until
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client

_PORT  = 19999
_TOKEN = "smoke-test-token"  # noqa: S105
_URL   = f"http://127.0.0.1:{_PORT}/mcp"


async def main() -> None:
    env = {**os.environ, "SOOTOOL_AUTH_TOKEN": _TOKEN}
    cmd = [
        sys.executable, "-m", "sootool", "--transport", "http",
        "--http-port", str(_PORT), "--log-format", "text",
    ]
    proc = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)  # noqa: S603
    try:
        wait_until(http_ready(_PORT), proc, "http server")
        print(f"Server ready on port {_PORT}")

        try:
            urllib.request.urlopen(urllib.request.Request(_URL, method="POST", data=b"{}"), timeout=5)  # noqa: S310
            check(False, "unauthenticated request must be rejected")
        except urllib.error.HTTPError as exc:
            check(exc.code == 401, f"unauthenticated request rejected with {exc.code}")

        http_client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {_TOKEN}"})
        async with Client(streamable_http_client(_URL, http_client=http_client)) as client:
            await run_checks(client)
    finally:
        stop(proc)


if __name__ == "__main__":
    asyncio.run(main())
