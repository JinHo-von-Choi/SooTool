"""
MCP stdio integration smoke test for SooTool.

Starts the server as a subprocess via stdio transport, connects with the
official MCP Python SDK, and verifies 5 tool calls produce expected values.

Run:
    uv run python scripts/mcp_smoke_test.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ---------------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------------

def _extract(result: Any) -> dict[str, Any]:
    """Parse the first content block's text as JSON."""
    content = result.content
    if not content:
        raise ValueError("empty content list in tool result")
    text = content[0].text  # type: ignore[union-attr]
    return json.loads(text)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def _assert(condition: bool, msg: str) -> None:
    if not condition:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK  : {msg}")


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

async def main() -> None:
    params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "sootool"],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ----------------------------------------------------------------
            # 1. tools/list
            # ----------------------------------------------------------------
            tools_resp = await session.list_tools()
            tool_count = len(tools_resp.tools)
            print(f"[1] tools/list: {tool_count} tools")
            _assert(tool_count > 20, f"expected > 20 tools, got {tool_count}")

            # ----------------------------------------------------------------
            # 2. core.add  1.5 + 2.5 = 4
            # ----------------------------------------------------------------
            r = await session.call_tool("core.add", {"operands": ["1.5", "2.5"]})
            d = _extract(r)
            print(f"[2] core.add: {d}")
            _assert(Decimal(d["result"]) == Decimal("4"), f"expected 4, got {d['result']}")

            # ----------------------------------------------------------------
            # 3. accounting.vat_extract  gross=11000, rate=0.1 → net=10000 vat=1000
            # ----------------------------------------------------------------
            r = await session.call_tool(
                "accounting.vat_extract",
                {"gross": "11000", "rate": "0.1"},
            )
            d = _extract(r)
            print(f"[3] accounting.vat_extract: {d}")
            _assert(Decimal(d["net"]) == Decimal("10000"), f"expected net=10000, got {d['net']}")
            _assert(Decimal(d["vat"]) == Decimal("1000"), f"expected vat=1000, got {d['vat']}")

            # ----------------------------------------------------------------
            # 4. finance.npv  rate=0.1, cashflows=[-100,50,60,70] → npv > 47
            # ----------------------------------------------------------------
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

            # ----------------------------------------------------------------
            # 5. datetime.age  birth=1990-06-15, ref=2026-04-22 → years=35
            # ----------------------------------------------------------------
            r = await session.call_tool(
                "datetime.age",
                {"birth_date": "1990-06-15", "reference_date": "2026-04-22"},
            )
            d = _extract(r)
            print(f"[5] datetime.age: {d}")
            _assert(d["years"] == 35, f"expected years=35, got {d['years']}")

            # ----------------------------------------------------------------
            # 6. tax.progressive  taxable_income=50000000, KR-style brackets
            # ----------------------------------------------------------------
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

    print("\nAll smoke tests PASSED.")


if __name__ == "__main__":
    asyncio.run(main())
