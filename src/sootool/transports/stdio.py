from __future__ import annotations

from mcp.server.mcpserver import MCPServer


class StdioTransport:
    def __init__(self, server: MCPServer) -> None:
        self._server = server

    async def start_async(self) -> None:
        await self._server.run_stdio_async()
