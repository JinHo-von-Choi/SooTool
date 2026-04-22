from __future__ import annotations

import argparse

from sootool.server import _load_modules, build_server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=10535)
    args = parser.parse_args()

    _load_modules()
    server = build_server()

    if args.transport == "stdio":
        server.run("stdio")
    else:
        server.run(  # type: ignore[call-arg]
            "streamable-http", host="0.0.0.0", port=args.port  # noqa: S104
        )


if __name__ == "__main__":
    main()
