"""
MCP HTTP+SSE legacy (2024-11) smoke test for SooTool.

Starts the server with --transport sse-legacy, connects using the MCP Python
SDK SSE client, and verifies the same 6 tool calls as mcp_smoke_stdio.py.

Run:
    uv run python scripts/mcp_smoke_sse.py
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from decimal import Decimal
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

_PORT    = 19996
_TOKEN   = "smoke-test-token"  # noqa: S105
_BASE    = f"http://127.0.0.1:{_PORT}"
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
    deadline = time.monotonic() + _TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _, stderr = proc.communicate()
            raise RuntimeError(
                f"server exited early (rc={proc.returncode})\n"
                f"stderr: {stderr.decode()}"
            )
        try:
            with urllib.request.urlopen(  # noqa: S310
                f"{_BASE}/healthz", timeout=2
            ):
                return
        except Exception:
            await asyncio.sleep(0.25)
    raise TimeoutError(f"server did not start within {_TIMEOUT}s")


async def main() -> None:
    env = dict(os.environ)
    env["SOOTOOL_AUTH_TOKEN"] = _TOKEN

    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "sse-legacy",
        "--sse-port", str(_PORT),
        "--auth-token", _TOKEN,
        "--log-format", "text",
    ]

    proc = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)  # noqa: S603
    try:
        await _wait_for_server(proc)
        print(f"Server ready on SSE legacy port {_PORT}")

        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {_TOKEN}"},
        )
        async with sse_client(
            f"{_BASE}/sse",
            sse_read_timeout=30,
            httpx_client_factory=lambda **_: http_client,  # type: ignore[arg-type]
        ) as (read, write):
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
                _assert(Decimal(d["npv"]) > Decimal("47"), f"expected npv > 47, got {d['npv']}")

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

        print("\nAll SSE legacy smoke tests PASSED.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
