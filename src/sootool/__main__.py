from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from sootool.observability.log_format import JsonFormatter
from sootool.server import DEFAULT_PROFILE, PROFILES, _load_modules, build_server

_VALID_TRANSPORTS = {"stdio", "http", "sse-legacy", "unix"}
_REMOVED_TRANSPORTS = {
    "websocket": "the WebSocket transport was removed (it is not part of MCP and MCP SDK v2 dropped it). "
                 "Use http (Streamable HTTP) instead.",
}
_NETWORK_TRANSPORTS = {"http", "sse-legacy"}


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
            socket_path = getattr(args, "socket", None) or os.environ.get("SOOTOOL_SOCKET_PATH")
            if socket_path:
                base.append("unix")
        return base
    parts = [t.strip() for t in raw.split(",") if t.strip()]
    for name in parts:
        if name in _REMOVED_TRANSPORTS:
            raise argparse.ArgumentTypeError(f"transport {name!r}: {_REMOVED_TRANSPORTS[name]}")
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
    admin_token: str | None = None,
    remote_admin: bool = False,
) -> None:
    effective_token = auth_token or os.environ.get("SOOTOOL_AUTH_TOKEN")
    effective_admin = admin_token or os.environ.get("SOOTOOL_ADMIN_TOKEN")
    networked = any(t in transports for t in _NETWORK_TRANSPORTS)
    if host != "127.0.0.1" and not (effective_token or effective_admin) and networked:
        sys.exit(
            "ERROR: --host is set to a non-loopback address but no authentication token is "
            "configured.\n"
            "Set SOOTOOL_AUTH_TOKEN or pass --auth-token <token> to enable bearer auth "
            "before exposing the server externally."
        )
    if remote_admin:
        if not networked:
            sys.exit("ERROR: --remote-admin applies only to network transports (http, sse-legacy).")
        if not effective_admin:
            sys.exit(
                "ERROR: --remote-admin requires an admin token. "
                "Set SOOTOOL_ADMIN_TOKEN or pass --admin-token <token>."
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
            "Valid: stdio, http, sse-legacy (deprecated), unix. Default: stdio."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Network bind address (default 127.0.0.1)")
    parser.add_argument("--http-port", type=int, default=10535, dest="http_port", help="Streamable HTTP port")
    parser.add_argument("--sse-port",  type=int, default=10536, dest="sse_port",  help="SSE legacy port (default 10536)")
    parser.add_argument("--auth-token", default=None, dest="auth_token", help="Bearer token for network transports (read scope)")
    parser.add_argument(
        "--admin-token",
        default=None,
        dest="admin_token",
        help="Bearer token granting the policy-write scope on network transports. Also: SOOTOOL_ADMIN_TOKEN",
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        default=False,
        dest="admin",
        help="Enable admin mode (policy write tools). Same as SOOTOOL_ADMIN_MODE=1.",
    )
    parser.add_argument(
        "--remote-admin",
        action="store_true",
        default=False,
        dest="remote_admin",
        help=(
            "Expose policy write tools on network transports. Requires --admin-token and admin mode. "
            "Without it write tools are available only on stdio and unix transports."
        ),
    )
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
        help="Enable the deprecated HTTP+SSE transport (MCP 2024-11). Also: SOOTOOL_ENABLE_SSE_LEGACY=1",
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
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=None,
        dest="profile",
        help=(
            "Tool exposure profile. full: every tool. lean: search/describe/call facade only "
            f"(smaller context cost). Also: SOOTOOL_PROFILE. Default: {DEFAULT_PROFILE}."
        ),
    )
    parser.add_argument("--log-format", choices=["json", "text"], default="json", dest="log_format")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        dest="log_level",
    )
    return parser


def _resolve_profile(args: argparse.Namespace) -> str:
    profile = getattr(args, "profile", None) or os.environ.get("SOOTOOL_PROFILE") or DEFAULT_PROFILE
    if profile not in PROFILES:
        sys.exit(f"ERROR: unknown profile {profile!r} (valid: {', '.join(PROFILES)})")
    return profile


async def _run(transports: list[str], args: argparse.Namespace) -> None:
    profile = _resolve_profile(args)

    from sootool.transports.http import HttpTransport
    from sootool.transports.sse_legacy import SseLegacyTransport
    from sootool.transports.stdio import StdioTransport
    from sootool.transports.unix import UnixTransport

    # 쓰기(정책 관리) 도구는 로컬 전송(stdio, unix)에만 노출한다. 네트워크 전송은 --remote-admin 일 때만 노출.
    local_server  = build_server(profile=profile, expose_writes=True)
    remote_server = build_server(profile=profile, expose_writes=args.remote_admin)

    tasks = []

    if "stdio" in transports and any(t in transports for t in _NETWORK_TRANSPORTS):
        logging.getLogger("sootool").warning(
            "Running stdio and network transport(s) simultaneously. When managed by "
            "systemd/supervisor, ensure stdin/stdout are not shared with HTTP processes."
        )

    if "stdio" in transports:
        tasks.append(StdioTransport(local_server).start_async())

    if "http" in transports:
        tasks.append(
            HttpTransport(
                server=remote_server,
                host=args.host,
                port=args.http_port,
                auth_token=args.auth_token,
                admin_token=args.admin_token,
                cors_origins=args.cors_origins,
                log_level=args.log_level.lower(),
            ).start_async()
        )

    if "sse-legacy" in transports:
        tasks.append(
            SseLegacyTransport(
                server=remote_server,
                host=args.host,
                port=args.sse_port,
                auth_token=args.auth_token,
                admin_token=args.admin_token,
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
                server=local_server,
                socket_path=args.socket,
                socket_mode=socket_mode,
                force=args.force_socket,
                log_level=args.log_level.lower(),
            ).start_async()
        )

    if not tasks:
        sys.exit("No transports selected.")

    await asyncio.gather(*tasks)


def main() -> None:
    """서브커맨드(call, tools 등)가 있으면 CLI 로, 없으면 서버로 기동한다."""
    from sootool.cli.main import SUBCOMMANDS, run

    argv = sys.argv[1:]
    if argv and argv[0] in SUBCOMMANDS:
        sys.exit(run(argv))
    if argv and argv[0] == "serve":
        sys.argv = [sys.argv[0], *argv[1:]]
    serve()


def serve() -> None:
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
    unix_path = args.socket or os.environ.get("SOOTOOL_SOCKET_PATH")
    if unix_path and "unix" not in transports and args.transport.strip() != "all":
        transports.append("unix")

    _validate_security(args.host, args.auth_token, transports, args.admin_token, args.remote_admin)

    if args.admin:
        os.environ["SOOTOOL_ADMIN_MODE"] = "1"

    _load_modules()
    asyncio.run(_run(transports, args))


if __name__ == "__main__":
    main()
