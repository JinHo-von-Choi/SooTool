from __future__ import annotations

import importlib.metadata

from starlette.requests import Request
from starlette.responses import JSONResponse

from sootool.core.registry import REGISTRY
from sootool.observability.log_format import uptime_seconds


def _get_version() -> str:
    try:
        return importlib.metadata.version("sootool")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


async def healthz(request: Request) -> JSONResponse:  # noqa: ARG001
    tool_count = len(REGISTRY.list())
    return JSONResponse(
        {
            "status":    "ok",
            "tools":     tool_count,
            "version":   _get_version(),
            "uptime_s":  uptime_seconds(),
        }
    )
