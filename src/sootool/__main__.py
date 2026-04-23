from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from sootool.observability.log_format import JsonFormatter
from sootool.server import _load_modules, build_server

_VALID_TRANSPORTS = {"stdio", "http"}


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


def _parse_transports(raw: str) -> list[str]:
    if raw.strip() == "all":
        return list(_VALID_TRANSPORTS)
    parts = [t.strip() for t in raw.split(",") if t.strip()]
    unknown = set(parts) - _VALID_TRANSPORTS
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown transport(s): {', '.join(sorted(unknown))}. "
            f"valid choices: {', '.join(sorted(_VALID_TRANSPORTS))}"
        )
    return parts


def _validate_security(host: str, auth_token: str | None) -> None:
    effective_token = auth_token or os.environ.get("SOOTOOL_AUTH_TOKEN")
    if host != "127.0.0.1" and not effective_token:
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
        help="Transport(s) to activate. Comma-separated or 'all'. "
             "Valid: stdio, http. Default: stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Network bind address (default 127.0.0.1)")
    parser.add_argument("--http-port", type=int, default=10535, dest="http_port", help="Streamable HTTP port")
    parser.add_argument("--auth-token", default=None, dest="auth_token", help="Bearer token for HTTP auth")
    parser.add_argument(
        "--cors-origin",
        action="append",
        default=[],
        dest="cors_origins",
        metavar="ORIGIN",
        help="Allowed CORS origin (repeatable). Falls back to SOOTOOL_CORS_ORIGINS env.",
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
    from sootool.transports.stdio import StdioTransport

    tasks = []

    if "stdio" in transports and "http" in transports:
        logging.getLogger("sootool").warning(
            "Running stdio and http simultaneously. When managed by systemd/supervisor, "
            "ensure stdin/stdout are not shared with the HTTP transport process."
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

    if not tasks:
        sys.exit("No transports selected.")

    await asyncio.gather(*tasks)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _configure_logging(args.log_format, args.log_level)

    try:
        transports = _parse_transports(args.transport)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    if "http" in transports:
        _validate_security(args.host, args.auth_token)

    _load_modules()
    asyncio.run(_run(transports, args))


if __name__ == "__main__":
    main()
