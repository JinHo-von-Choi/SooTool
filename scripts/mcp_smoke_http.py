"""
MCP HTTP integration smoke test for SooTool.

Starts the server as a subprocess via streamable-HTTP transport, connects with
the official MCP Python SDK HTTP client, and verifies the same 6 tool calls
as mcp_smoke_stdio.py produce expected values.

Run:
    uv run python scripts/mcp_smoke_http.py
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from decimal import Decimal
from typing import Any

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


_PORT    = 19999
_TOKEN   = "smoke-test-token"
_BASE    = f"http://127.0.0.1:{_PORT}/mcp"
_TIMEOUT = 20


def _extract(result: Any) -> dict[str, Any]:
    content = result.content
    if not content:
        raise ValueError("empty content list in tool result")
    text = content[0].text  # type: ignore[union-attr]
    return json.loads(text)  # type: ignore[no-any-return]


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK  : {msg}")


async def _wait_for_server(proc: subprocess.Popen[bytes]) -> None:
    import urllib.request

    deadline = time.monotonic() + _TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            raise RuntimeError(
                f"server process exited early (rc={proc.returncode})\n"
                f"stderr: {stderr.decode()}"
            )
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/healthz", timeout=2):
                return
        except Exception:
            await asyncio.sleep(0.25)
    raise TimeoutError(f"server did not start within {_TIMEOUT}s")


async def main() -> None:
    env = dict(os.environ)
    env["SOOTOOL_AUTH_TOKEN"] = _TOKEN

    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "http",
        "--http-port", str(_PORT),
        "--auth-token", _TOKEN,
        "--log-format", "text",
    ]

    proc = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)
    try:
        await _wait_for_server(proc)
        print(f"Server ready on port {_PORT}")

        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        async with streamable_http_client(
            _BASE,
            http_client=http_client,
        ) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_resp = await session.list_tools()
                tool_count = len(tools_resp.tools)
                print(f"[1] tools/list: {tool_count} tools")
                _assert(tool_count > 20, f"expected > 20 tools, got {tool_count}")

                r = await session.call_tool("core.add", {"operands": ["1.5", "2.5"]})
                d = _extract(r)
                print(f"[2] core.add: {d}")
                _assert(Decimal(d["result"]) == Decimal("4"), f"expected 4, got {d['result']}")

                r = await session.call_tool(
                    "accounting.vat_extract",
                    {"gross": "11000", "rate": "0.1"},
                )
                d = _extract(r)
                print(f"[3] accounting.vat_extract: {d}")
                _assert(Decimal(d["net"]) == Decimal("10000"), f"expected net=10000, got {d['net']}")
                _assert(Decimal(d["vat"]) == Decimal("1000"), f"expected vat=1000, got {d['vat']}")

                r = await session.call_tool(
                    "finance.npv",
                    {"rate": "0.1", "cashflows": ["-100", "50", "60", "70"]},
                )
                d = _extract(r)
                print(f"[4] finance.npv: {d}")
                _assert(
                    Decimal(d["npv"]) > Decimal("47"),
                    f"expected npv > 47, got {d['npv']}",
                )

                r = await session.call_tool(
                    "datetime.age",
                    {"birth_date": "1990-06-15", "reference_date": "2026-04-22"},
                )
                d = _extract(r)
                print(f"[5] datetime.age: {d}")
                _assert(d["years"] == 35, f"expected years=35, got {d['years']}")

                brackets = [
                    {"upper": "14000000", "rate": "0.06"},
                    {"upper": "50000000", "rate": "0.15"},
                    {"upper": None,        "rate": "0.24"},
                ]
                r = await session.call_tool(
                    "tax.progressive",
                    {"taxable_income": "50000000", "brackets": brackets},
                )
                d = _extract(r)
                print(f"[6] tax.progressive: {d}")
                _assert(
                    Decimal(d["tax"]) == Decimal("6240000"),
                    f"expected tax=6240000, got {d['tax']}",
                )

        print("\nAll HTTP smoke tests PASSED.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
