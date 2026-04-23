"""
MCP Unix Domain Socket smoke test for SooTool.

Starts the server with --transport unix, connects via Unix socket using
newline-framed JSON-RPC, and verifies the same 6 tool calls.

Run:
    uv run python scripts/mcp_smoke_unix.py
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

_TIMEOUT = 20
_TOKEN   = "smoke-test-token"  # noqa: S105


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK  : {msg}")


async def _wait_for_socket(sock_path: str, proc: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + _TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _, stderr = proc.communicate()
            raise RuntimeError(
                f"server exited early (rc={proc.returncode})\n"
                f"stderr: {stderr.decode()}"
            )
        if Path(sock_path).exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(sock_path)
                    return
            except OSError:
                pass
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Unix socket not ready within {_TIMEOUT}s")


class _UnixSession:
    """Minimal JSON-RPC over Unix socket (newline-framed)."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._seq  = 0
        self._buf  = b""

    def _send(self, payload: dict[str, Any]) -> None:  # type: ignore[type-arg]
        frame = (json.dumps(payload) + "\n").encode()
        self._sock.sendall(frame)

    def _recv_line(self) -> bytes:
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionError("connection closed by server")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:  # type: ignore[type-arg]
        self._seq += 1
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": self._seq, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        while True:
            raw = self._recv_line()
            if not raw.strip():
                continue
            resp = json.loads(raw)
            if resp.get("id") == self._seq:
                return resp  # type: ignore[no-any-return]


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "smoke.sock")

        cmd = [
            sys.executable, "-m", "sootool",
            "--transport", "unix",
            "--socket", sock_path,
            "--log-format", "text",
        ]

        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603
        try:
            await _wait_for_socket(sock_path, proc)
            print(f"Server ready on Unix socket {sock_path}")

            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(10.0)
                sock.connect(sock_path)
                session = _UnixSession(sock)

                # 1. initialize
                resp = session.request(
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "clientInfo": {"name": "smoke-unix", "version": "0.1"},
                        "capabilities": {},
                    },
                )
                _assert("result" in resp, "initialize returned result")

                # 2. tools/list
                resp = session.request("tools/list")
                tools = resp["result"].get("tools", [])
                tool_count = len(tools)
                print(f"[1] tools/list: {tool_count} tools")
                _assert(tool_count > 20, f"expected > 20 tools, got {tool_count}")

                # 3. core.add
                resp = session.request(
                    "tools/call",
                    {"name": "core.add", "arguments": {"operands": ["1.5", "2.5"]}},
                )
                d = json.loads(resp["result"]["content"][0]["text"])
                print(f"[2] core.add: {d}")
                _assert(Decimal(d["result"]) == Decimal("4"), f"expected 4, got {d['result']}")

                # 4. accounting.vat_extract
                resp = session.request(
                    "tools/call",
                    {"name": "accounting.vat_extract", "arguments": {"gross": "11000", "rate": "0.1"}},
                )
                d = json.loads(resp["result"]["content"][0]["text"])
                print(f"[3] accounting.vat_extract: {d}")
                _assert(Decimal(d["net"]) == Decimal("10000"), f"expected net=10000, got {d['net']}")
                _assert(Decimal(d["vat"]) == Decimal("1000"), f"expected vat=1000, got {d['vat']}")

                # 5. finance.npv
                resp = session.request(
                    "tools/call",
                    {"name": "finance.npv", "arguments": {"rate": "0.1", "cashflows": ["-100", "50", "60", "70"]}},
                )
                d = json.loads(resp["result"]["content"][0]["text"])
                print(f"[4] finance.npv: {d}")
                _assert(Decimal(d["npv"]) > Decimal("47"), f"expected npv > 47, got {d['npv']}")

                # 6. datetime.age
                resp = session.request(
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
                resp = session.request(
                    "tools/call",
                    {"name": "tax.progressive", "arguments": {"taxable_income": "50000000", "brackets": brackets}},
                )
                d = json.loads(resp["result"]["content"][0]["text"])
                print(f"[6] tax.progressive: {d}")
                _assert(
                    Decimal(d["tax"]) == Decimal("6240000"),
                    f"expected tax=6240000, got {d['tax']}",
                )

            print("\nAll Unix socket smoke tests PASSED.")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
