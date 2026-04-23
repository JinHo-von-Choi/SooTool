"""Unix Domain Socket transport for SooTool MCP server.

Reuses the same JSON-RPC newline-framed protocol as stdio.
Each line is a complete JSON-RPC message; responses are newline-terminated.

CLI:
    --transport unix --socket /path/to/sootool.sock
    --socket-mode 0600   (octal, default 0600)
    --force-socket       (remove stale socket file on startup)

Environment:
    SOOTOOL_SOCKET_PATH   — default socket path
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import stat
from pathlib import Path

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.shared.session import SessionMessage  # type: ignore[attr-defined]
from mcp.types import JSONRPCMessage

logger = logging.getLogger("sootool.unix")

_DEFAULT_SOCKET_PATH = "/tmp/sootool.sock"  # noqa: S108
_DEFAULT_MODE        = 0o600


def _effective_socket_path(cli_path: str | None) -> str:
    return cli_path or os.environ.get("SOOTOOL_SOCKET_PATH", _DEFAULT_SOCKET_PATH)


class UnixTransport:
    """MCP server transport over a Unix domain socket.

    Wire protocol mirrors stdio: each message is a JSON object terminated
    by a newline (``\\n``).  The server reads one JSON-RPC request per line
    and writes one JSON-RPC response per line back to the same connection.
    """

    def __init__(
        self,
        server: FastMCP,
        socket_path: str | None,
        socket_mode: int = _DEFAULT_MODE,
        force: bool = False,
    ) -> None:
        self._server      = server
        self._socket_path = _effective_socket_path(socket_path)
        self._socket_mode = socket_mode
        self._force       = force

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_async(self) -> None:
        path = Path(self._socket_path)

        self._check_or_remove_stale(path)

        logger.info(
            "Unix socket transport starting on %s (mode=%o)",
            path,
            self._socket_mode,
        )

        server = await asyncio.start_unix_server(
            self._handle_connection,
            path=str(path),
        )

        # Apply requested filesystem permissions.
        try:
            os.chmod(str(path), self._socket_mode)
        except OSError as exc:
            logger.warning("Could not set socket permissions: %s", exc)

        try:
            async with server:
                await server.serve_forever()
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_or_remove_stale(self, path: Path) -> None:
        """Refuse to start if the socket file exists and --force-socket not set."""
        if not path.exists():
            return

        # Confirm it really is a socket (could be a regular file left by crash)
        try:
            mode = path.stat().st_mode
        except OSError:
            return  # can't stat — proceed and let bind fail

        if stat.S_ISSOCK(mode):
            if self._force:
                logger.warning(
                    "Removing stale socket file at %s (--force-socket)", path
                )
                try:
                    path.unlink()
                except OSError as exc:
                    raise RuntimeError(
                        f"Could not remove stale socket at {path}: {exc}"
                    ) from exc
            else:
                raise RuntimeError(
                    f"Socket file already exists at {path}. "
                    "If this is a stale file from a previous run, remove it or "
                    "restart with --force-socket."
                )
        else:
            # Not a socket — something unexpected is there; refuse to overwrite.
            raise RuntimeError(
                f"Path {path} exists and is not a Unix socket. "
                "Remove it manually before starting SooTool."
            )

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername", "<unknown>")
        logger.info("Unix socket: new connection from %s", peer)

        mcp_server = self._server._mcp_server

        # Create in-memory streams to bridge asyncio streams ↔ MCP server.
        client_to_server_w, client_to_server_r = anyio.create_memory_object_stream(
            max_buffer_size=64,
        )
        server_to_client_w, server_to_client_r = anyio.create_memory_object_stream(
            max_buffer_size=64,
        )

        async def recv_loop() -> None:
            try:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    line = line.rstrip(b"\n")
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                        rpc_msg = JSONRPCMessage.model_validate(payload)
                        await client_to_server_w.send(SessionMessage(rpc_msg))
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Unix socket: invalid JSON-RPC frame: %s", exc)
            finally:
                await client_to_server_w.aclose()

        async def send_loop() -> None:
            try:
                async for session_msg in server_to_client_r:
                    try:
                        frame = session_msg.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        writer.write((frame + "\n").encode())
                        await writer.drain()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Unix socket: send error: %s", exc)
                        break
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:  # noqa: BLE001, S110
                    logger.debug("Unix socket: writer close error")

        async def mcp_server_task() -> None:
            await mcp_server.run(
                client_to_server_r,
                server_to_client_w,
                mcp_server.create_initialization_options(),
            )

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(recv_loop)
                tg.start_soon(send_loop)
                tg.start_soon(mcp_server_task)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Unix socket session ended: %s", exc)
        finally:
            try:
                writer.close()
            except Exception:  # noqa: BLE001, S110
                logger.debug("Unix socket: final writer close error")
            logger.info("Unix socket: connection closed (%s)", peer)
