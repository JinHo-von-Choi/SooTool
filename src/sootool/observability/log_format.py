from __future__ import annotations

import json
import logging
import time
from typing import Any

_SENSITIVE_KEYS = frozenset({"authorization", "cookie", "auth-token", "x-auth-token"})
_START_TIME = time.monotonic()


def uptime_seconds() -> int:
    return int(time.monotonic() - _START_TIME)


def mask_sensitive(headers: dict[str, str]) -> dict[str, str]:
    return {
        k: "***" if k.lower() in _SENSITIVE_KEYS else v
        for k, v in headers.items()
    }


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        import datetime

        data: dict[str, Any] = {
            "ts":      datetime.datetime.now(datetime.UTC).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra", None)
        if extra:
            data.update(extra)
        return json.dumps(data, default=str)
