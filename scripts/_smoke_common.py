"""전송별 MCP 스모크 스크립트가 공유하는 검증과 서버 기동 보조 코드."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from mcp.client import Client

TIMEOUT_S = 25


def check(condition: bool, msg: str) -> None:
    if not condition:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK  : {msg}")


async def run_checks(client: Client) -> None:
    """같은 6개 도구 호출과 오류 계약을 어느 전송에서든 검증한다."""
    tools = await client.list_tools()
    count = len(tools.tools)
    print(f"[1] tools/list: {count} tools")
    check(count > 20, f"expected > 20 tools, got {count}")

    r = await client.call_tool("core.add", {"operands": ["1.5", "2.5"]})
    d = r.structured_content or {}
    print(f"[2] core.add: {d.get('result')}")
    check(Decimal(d["result"]) == Decimal("4"), f"expected 4, got {d['result']}")
    check("integrity" in d["_meta"], "response carries _meta.integrity")

    r = await client.call_tool("accounting.vat_extract", {"gross": "11000", "rate": "0.1"})
    d = r.structured_content or {}
    print(f"[3] accounting.vat_extract: net={d.get('net')} vat={d.get('vat')}")
    check(Decimal(d["net"]) == Decimal("10000"), f"expected net=10000, got {d['net']}")
    check(Decimal(d["vat"]) == Decimal("1000"), f"expected vat=1000, got {d['vat']}")

    r = await client.call_tool("finance.npv", {"rate": "0.1", "cashflows": ["-100", "50", "60", "70"]})
    d = r.structured_content or {}
    print(f"[4] finance.npv: {d.get('npv')}")
    check(Decimal(d["npv"]) > Decimal("47"), f"expected npv > 47, got {d['npv']}")

    r = await client.call_tool("datetime.age", {"birth_date": "1990-06-15", "reference_date": "2026-04-22"})
    d = r.structured_content or {}
    print(f"[5] datetime.age: years={d.get('years')}")
    check(d["years"] == 35, f"expected years=35, got {d['years']}")

    brackets = [
        {"upper": "14000000", "rate": "0.06"},
        {"upper": "50000000", "rate": "0.15"},
        {"upper": None,        "rate": "0.24"},
    ]
    r = await client.call_tool("tax.progressive", {"taxable_income": "50000000", "brackets": brackets})
    d = r.structured_content or {}
    print(f"[6] tax.progressive: tax={d.get('tax')}")
    check(Decimal(d["tax"]) == Decimal("6240000"), f"expected tax=6240000, got {d['tax']}")

    r = await client.call_tool("core.add", {"operands": ["abc"]})
    err: dict[str, Any] = (r.structured_content or {}).get("error", {})
    print(f"[7] error contract: {err.get('code')}")
    check(bool(r.is_error) and err.get("code") == "invalid_number", "invalid number yields isError with code")

    print("\nAll smoke tests PASSED.")


def wait_until(ready: Callable[[], bool], proc: subprocess.Popen[bytes], what: str) -> None:
    """``ready`` 가 참이 될 때까지 기다린다. 서버 프로세스가 먼저 끝나면 stderr 와 함께 실패한다."""
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _, stderr = proc.communicate()
            raise RuntimeError(f"server exited early (rc={proc.returncode})\n{stderr.decode()}")
        try:
            if ready():
                return
        except OSError:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"{what} not ready within {TIMEOUT_S}s")


def http_ready(port: int) -> Callable[[], bool]:
    def _ready() -> bool:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2):  # noqa: S310
            return True
    return _ready


def socket_ready(path: Path) -> Callable[[], bool]:
    return lambda: path.exists()


def stop(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
