"""Unix 도메인 소켓 전송: UDS 위의 Streamable HTTP.

TCP 대신 Unix 소켓에서 같은 Streamable HTTP 앱(무상태)을 서비스한다. 접근 통제는 소켓 파일
권한(기본 0600)이 맡으므로 Bearer 인증은 두지 않는다. 클라이언트는 UDS 를 지원하는 HTTP
클라이언트(예: httpx 의 ``uds`` 전송)로 ``/mcp`` 에 접속한다.

CLI:
    --transport unix --socket /path/to/sootool.sock
    --socket-mode 0600   (octal, default 0600)
    --force-socket       (remove stale socket file on startup)

Environment:
    SOOTOOL_SOCKET_PATH   default socket path
"""
from __future__ import annotations

import logging
import os
import socket
import stat
from pathlib import Path

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from sootool.policy_mgmt.paths import ensure_private_dir, get_runtime_dir
from sootool.transports.http import build_http_app

logger = logging.getLogger("sootool.unix")

_DEFAULT_MODE = 0o600
_DEFAULT_NAME = "sootool.sock"


def _effective_socket_path(cli_path: str | None) -> str:
    explicit = cli_path or os.environ.get("SOOTOOL_SOCKET_PATH")
    if explicit:
        return explicit
    runtime = get_runtime_dir() / "sootool"
    ensure_private_dir(runtime)
    return str(runtime / _DEFAULT_NAME)


class UnixTransport:
    """MCP 서버를 Unix 도메인 소켓에서 Streamable HTTP 로 서비스한다."""

    def __init__(
        self,
        server:      MCPServer,
        socket_path: str | None,
        socket_mode: int  = _DEFAULT_MODE,
        force:       bool = False,
        log_level:   str  = "info",
    ) -> None:
        self._server      = server
        self._socket_path = _effective_socket_path(socket_path)
        self._socket_mode = socket_mode
        self._force       = force
        self._log_level   = log_level

    async def start_async(self) -> None:
        path = Path(self._socket_path)
        self._check_or_remove_stale(path)

        logger.info("Unix socket transport starting on %s (mode=%o)", path, self._socket_mode)
        sock = self._bind_socket(path)

        # 브라우저가 접근할 수 없는 로컬 소켓이므로 Host 헤더 제한(DNS 리바인딩 보호)은 의미가 없다.
        # 접근 통제는 소켓 파일 권한이 맡는다.
        app = build_http_app(
            self._server, None, [], require_auth=False,
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        config = uvicorn.Config(app, log_level=self._log_level, loop="asyncio")
        try:
            await uvicorn.Server(config).serve(sockets=[sock])
        finally:
            sock.close()
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove socket file %s", path)

    def _bind_socket(self, path: Path) -> socket.socket:
        """요청한 권한으로 소켓 파일을 만든다.

        바인드 순간부터 권한이 제한되도록 umask 를 잠시 좁힌다. 소켓 파일은 바인드 시점에 만들어지므로
        바인드 후 chmod 만 쓰면 그 사이에 다른 사용자가 접속할 수 있는 틈이 생긴다.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        previous_umask = os.umask(0o777 & ~self._socket_mode)
        try:
            sock.bind(str(path))
        except OSError:
            sock.close()
            raise
        finally:
            os.umask(previous_umask)
        os.chmod(str(path), self._socket_mode)
        return sock

    def _check_or_remove_stale(self, path: Path) -> None:
        """소켓 파일이 이미 있으면 --force-socket 이 아닌 한 기동을 거부한다."""
        if not path.exists():
            return

        try:
            mode = path.stat().st_mode
        except OSError:
            return  # stat 불가: 바인드 단계에서 오류가 드러난다

        if stat.S_ISSOCK(mode):
            if self._force:
                logger.warning("Removing stale socket file at %s (--force-socket)", path)
                try:
                    path.unlink()
                except OSError as exc:
                    raise RuntimeError(f"Could not remove stale socket at {path}: {exc}") from exc
            else:
                raise RuntimeError(
                    f"Socket file already exists at {path}. "
                    "If this is a stale file from a previous run, remove it or "
                    "restart with --force-socket."
                )
        else:
            raise RuntimeError(
                f"Path {path} exists and is not a Unix socket. "
                "Remove it manually before starting SooTool."
            )
