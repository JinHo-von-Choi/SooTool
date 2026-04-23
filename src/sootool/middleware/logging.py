from __future__ import annotations

import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from sootool.observability.log_format import mask_sensitive

logger = logging.getLogger("sootool.http")

_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "x-auth-token"})


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        from starlette.middleware.base import RequestResponseEndpoint

        _call_next: RequestResponseEndpoint = call_next  # type: ignore[assignment]

        start = time.monotonic()
        request_id = getattr(request.state, "request_id", "-")
        masked_headers = mask_sensitive(dict(request.headers))

        response = await _call_next(request)

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        extra: dict[str, Any] = {
            "transport":   "http",
            "request_id":  request_id,
            "method":      request.method,
            "path":        request.url.path,
            "status":      response.status_code,
            "latency_ms":  latency_ms,
            "headers":     masked_headers,
        }
        record = logging.LogRecord(
            name="sootool.http",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="request",
            args=(),
            exc_info=None,
        )
        record.__dict__["extra"] = extra
        logger.handle(record)

        return response
