"""
MCP stdio integration smoke test for SooTool.

Starts the server as a subprocess via stdio transport, connects with the
official MCP Python SDK, and verifies the tool calls and the error contract.

Run:
    uv run python scripts/mcp_smoke_test.py
"""
from __future__ import annotations

import asyncio
import sys

from _smoke_common import run_checks
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "sootool"])
    async with Client(params) as client:
        await run_checks(client)


if __name__ == "__main__":
    asyncio.run(main())
