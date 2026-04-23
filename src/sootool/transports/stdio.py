from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP


class StdioTransport:
    def __init__(self, server: FastMCP) -> None:
        self._server = server

    async def start_async(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._server.run, "stdio")
