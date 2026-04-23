from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from sootool.observability.log_format import JsonFormatter
from sootool.server import _load_modules, build_server

_VALID_TRANSPORTS = {"stdio", "http", "sse-legacy", "websocket", "unix"}


def _configure_logging(log_format: str, log_level: str) -> None:
    handler = logging.StreamHandler(sys.stderr)
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def _parse_transports(raw: str, args: argparse.Namespace | None = None) -> list[str]:
    if raw.strip() == "all":
        # "all" activates stdio + http + opt-in transports that are enabled
        base = ["stdio", "http"]
        if args is not None:
            if getattr(args, "enable_sse_legacy", False) or os.environ.get("SOOTOOL_ENABLE_SSE_LEGACY"):
                base.append("sse-legacy")
            if getattr(args, "enable_websocket", False) or os.environ.get("SOOTOOL_ENABLE_WEBSOCKET"):
                base.append("websocket")
            socket_path = getattr(args, "socket", None) or os.environ.get("SOOTOOL_SOCKET_PATH")
            if socket_path:
                base.append("unix")
        return base
    parts = [t.strip() for t in raw.split(",") if t.strip()]
    unknown = set(parts) - _VALID_TRANSPORTS
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown transport(s): {', '.join(sorted(unknown))}. "
            f"valid choices: {', '.join(sorted(_VALID_TRANSPORTS))}"
        )
    return parts


def _validate_security(
    host: str,
    auth_token: str | None,
    transports: list[str],
) -> None:
    effective_token = auth_token or os.environ.get("SOOTOOL_AUTH_TOKEN")
    network_transports = {"http", "sse-legacy", "websocket"}
    if host != "127.0.0.1" and not effective_token:
        if any(t in transports for t in network_transports):
            sys.exit(
                "ERROR: --host is set to a non-loopback address but no authentication token is "
                "configured.\n"
                "Set SOOTOOL_AUTH_TOKEN or pass --auth-token <token> to enable bearer auth "
                "before exposing the server externally."
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sootool",
        description="SooTool MCP server",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        help=(
            "Transport(s) to activate. Comma-separated or 'all'. "
            "Valid: stdio, http, sse-legacy, websocket, unix. Default: stdio."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Network bind address (default 127.0.0.1)")
    parser.add_argument("--http-port", type=int, default=10535, dest="http_port", help="Streamable HTTP port")
    parser.add_argument("--sse-port",  type=int, default=10536, dest="sse_port",  help="SSE legacy port (default 10536)")
    parser.add_argument("--ws-port",   type=int, default=10537, dest="ws_port",   help="WebSocket port (default 10537)")
    parser.add_argument("--auth-token", default=None, dest="auth_token", help="Bearer token for network transports")
    parser.add_argument(
        "--cors-origin",
        action="append",
        default=[],
        dest="cors_origins",
        metavar="ORIGIN",
        help="Allowed CORS origin (repeatable). Falls back to SOOTOOL_CORS_ORIGINS env.",
    )
    # SSE legacy
    parser.add_argument(
        "--enable-sse-legacy",
        action="store_true",
        default=False,
        dest="enable_sse_legacy",
        help="Enable HTTP+SSE legacy transport (MCP 2024-11). Also: SOOTOOL_ENABLE_SSE_LEGACY=1",
    )
    # WebSocket
    parser.add_argument(
        "--enable-websocket",
        action="store_true",
        default=False,
        dest="enable_websocket",
        help="Enable WebSocket transport. Also: SOOTOOL_ENABLE_WEBSOCKET=1",
    )
    # Unix socket
    parser.add_argument(
        "--socket",
        default=None,
        dest="socket",
        metavar="PATH",
        help="Unix domain socket path. Also: SOOTOOL_SOCKET_PATH",
    )
    parser.add_argument(
        "--socket-mode",
        default="0600",
        dest="socket_mode",
        metavar="MODE",
        help="Unix socket file permissions (octal, default 0600)",
    )
    parser.add_argument(
        "--force-socket",
        action="store_true",
        default=False,
        dest="force_socket",
        help="Remove stale Unix socket file on startup instead of refusing to start",
    )
    parser.add_argument("--log-format", choices=["json", "text"], default="json", dest="log_format")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        dest="log_level",
    )
    return parser


async def _run(transports: list[str], args: argparse.Namespace) -> None:
    server = build_server()

    from sootool.transports.http import HttpTransport
    from sootool.transports.sse_legacy import SseLegacyTransport
    from sootool.transports.stdio import StdioTransport
    from sootool.transports.unix import UnixTransport
    from sootool.transports.websocket import WebSocketTransport

    tasks = []

    if "stdio" in transports and any(t in transports for t in ("http", "sse-legacy", "websocket")):
        logging.getLogger("sootool").warning(
            "Running stdio and network transport(s) simultaneously. When managed by "
            "systemd/supervisor, ensure stdin/stdout are not shared with HTTP processes."
        )

    if "stdio" in transports:
        tasks.append(StdioTransport(server).start_async())

    if "http" in transports:
        tasks.append(
            HttpTransport(
                server=server,
                host=args.host,
                port=args.http_port,
                auth_token=args.auth_token,
                cors_origins=args.cors_origins,
                log_level=args.log_level.lower(),
            ).start_async()
        )

    if "sse-legacy" in transports:
        tasks.append(
            SseLegacyTransport(
                server=server,
                host=args.host,
                port=args.sse_port,
                auth_token=args.auth_token,
                cors_origins=args.cors_origins,
                log_level=args.log_level.lower(),
            ).start_async()
        )

    if "websocket" in transports:
        tasks.append(
            WebSocketTransport(
                server=server,
                host=args.host,
                port=args.ws_port,
                auth_token=args.auth_token,
                cors_origins=args.cors_origins,
                log_level=args.log_level.lower(),
            ).start_async()
        )

    if "unix" in transports:
        socket_mode_str = getattr(args, "socket_mode", "0600")
        try:
            socket_mode = int(socket_mode_str, 8)
        except ValueError:
            sys.exit(f"ERROR: invalid --socket-mode value: {socket_mode_str!r} (expected octal)")
        tasks.append(
            UnixTransport(
                server=server,
                socket_path=args.socket,
                socket_mode=socket_mode,
                force=args.force_socket,
            ).start_async()
        )

    if not tasks:
        sys.exit("No transports selected.")

    await asyncio.gather(*tasks)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _configure_logging(args.log_format, args.log_level)

    try:
        transports = _parse_transports(args.transport, args)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    # Opt-in flags augment explicit transport list
    if args.enable_sse_legacy and "sse-legacy" not in transports:
        transports.append("sse-legacy")
    if args.enable_websocket and "websocket" not in transports:
        transports.append("websocket")
    unix_path = args.socket or os.environ.get("SOOTOOL_SOCKET_PATH")
    if unix_path and "unix" not in transports and args.transport.strip() != "all":
        transports.append("unix")

    _validate_security(args.host, args.auth_token, transports)

    _load_modules()
    asyncio.run(_run(transports, args))


if __name__ == "__main__":
    main()
