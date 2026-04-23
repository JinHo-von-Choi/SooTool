"""
MCP WebSocket smoke test for SooTool.

Starts the server with --transport websocket, connects via raw WebSocket
using the JSON-RPC framing, and verifies the same 6 tool calls.

Run:
    uv run python scripts/mcp_smoke_ws.py
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

_PORT    = 19995
_TOKEN   = "smoke-test-token"  # noqa: S105
_BASE    = f"ws://127.0.0.1:{_PORT}/ws"
_TIMEOUT = 20


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK  : {msg}")


def _extract(text: str) -> dict[str, Any]:
    return json.loads(text)  # type: ignore[no-any-return]


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
                f"http://127.0.0.1:{_PORT}/healthz", timeout=2
            ):
                return
        except Exception:
            await asyncio.sleep(0.25)
    raise TimeoutError(f"server did not start within {_TIMEOUT}s")


class _WsSession:
    """Minimal JSON-RPC over WebSocket client."""

    def __init__(self, ws: Any) -> None:
        self._ws  = ws
        self._seq = 0

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:  # type: ignore[type-arg]
        self._seq += 1
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": self._seq, "method": method}
        if params is not None:
            msg["params"] = params
        await self._ws.send(json.dumps(msg))
        while True:
            raw = await self._ws.recv()
            resp = json.loads(raw)
            # Skip server-initiated notifications (no "id" or id != ours)
            if resp.get("id") == self._seq:
                return resp  # type: ignore[no-any-return]


async def _run_session() -> None:
    try:
        import websockets
    except ImportError:
        print("ERROR: websockets package not installed. Run: uv add websockets", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {_TOKEN}"}

    async with websockets.connect(_BASE, additional_headers=headers) as ws:  # type: ignore[attr-defined]
        session = _WsSession(ws)

        # 1. initialize
        resp = await session.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "smoke-ws", "version": "0.1"},
                "capabilities": {},
            },
        )
        _assert("result" in resp, "initialize returned result")

        # 2. tools/list
        resp = await session.request("tools/list")
        tools = resp["result"].get("tools", [])
        tool_count = len(tools)
        print(f"[1] tools/list: {tool_count} tools")
        _assert(tool_count > 20, f"expected > 20 tools, got {tool_count}")

        # 3. core.add
        resp = await session.request(
            "tools/call",
            {"name": "core.add", "arguments": {"operands": ["1.5", "2.5"]}},
        )
        content = resp["result"]["content"]
        d = json.loads(content[0]["text"])
        print(f"[2] core.add: {d}")
        _assert(Decimal(d["result"]) == Decimal("4"), f"expected 4, got {d['result']}")

        # 4. accounting.vat_extract
        resp = await session.request(
            "tools/call",
            {"name": "accounting.vat_extract", "arguments": {"gross": "11000", "rate": "0.1"}},
        )
        d = json.loads(resp["result"]["content"][0]["text"])
        print(f"[3] accounting.vat_extract: {d}")
        _assert(Decimal(d["net"]) == Decimal("10000"), f"expected net=10000, got {d['net']}")
        _assert(Decimal(d["vat"]) == Decimal("1000"), f"expected vat=1000, got {d['vat']}")

        # 5. finance.npv
        resp = await session.request(
            "tools/call",
            {"name": "finance.npv", "arguments": {"rate": "0.1", "cashflows": ["-100", "50", "60", "70"]}},
        )
        d = json.loads(resp["result"]["content"][0]["text"])
        print(f"[4] finance.npv: {d}")
        _assert(Decimal(d["npv"]) > Decimal("47"), f"expected npv > 47, got {d['npv']}")

        # 6. datetime.age
        resp = await session.request(
            "tools/call",
            {"name": "datetime.age", "arguments": {"birth_date": "1990-06-15", "reference_date": "2026-04-22"}},
        )
        d = json.loads(resp["result"]["content"][0]["text"])
        print(f"[5] datetime.age: {d}")
        _assert(d["years"] == 35, f"expected years=35, got {d['years']}")

        # 7. tax.progressive
        brackets = [
            {"upper": "14000000", "rate": "0.06"},
            {"upper": "50000000", "rate": "0.15"},
            {"upper": None,        "rate": "0.24"},
        ]
        resp = await session.request(
            "tools/call",
            {"name": "tax.progressive", "arguments": {"taxable_income": "50000000", "brackets": brackets}},
        )
        d = json.loads(resp["result"]["content"][0]["text"])
        print(f"[6] tax.progressive: {d}")
        _assert(
            Decimal(d["tax"]) == Decimal("6240000"),
            f"expected tax=6240000, got {d['tax']}",
        )


async def main() -> None:
    env = dict(os.environ)
    env["SOOTOOL_AUTH_TOKEN"] = _TOKEN

    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "websocket",
        "--ws-port", str(_PORT),
        "--auth-token", _TOKEN,
        "--log-format", "text",
    ]

    proc = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE)  # noqa: S603
    try:
        await _wait_for_server(proc)
        print(f"Server ready on WebSocket port {_PORT}")
        await _run_session()
        print("\nAll WebSocket smoke tests PASSED.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
