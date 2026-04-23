from __future__ import annotations

import json
import logging

from sootool.observability.log_format import JsonFormatter, mask_sensitive


def _make_record(msg: str, extra: dict | None = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if extra:
        record.__dict__["extra"] = extra
    return record


def test_json_formatter_produces_valid_json() -> None:
    formatter = JsonFormatter()
    record = _make_record("hello world")
    output = formatter.format(record)
    data = json.loads(output)
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert "ts" in data


def test_json_formatter_includes_extra_fields() -> None:
    formatter = JsonFormatter()
    extra = {"transport": "http", "latency_ms": 12.5}
    record = _make_record("req", extra=extra)
    data = json.loads(formatter.format(record))
    assert data["transport"] == "http"
    assert data["latency_ms"] == 12.5


def test_mask_sensitive_masks_authorization() -> None:
    headers = {"authorization": "Bearer secret", "content-type": "application/json"}
    masked = mask_sensitive(headers)
    assert masked["authorization"] == "***"
    assert masked["content-type"] == "application/json"


def test_mask_sensitive_masks_cookie() -> None:
    headers = {"cookie": "session=abc123"}
    assert mask_sensitive(headers)["cookie"] == "***"


def test_mask_sensitive_case_insensitive() -> None:
    headers = {"Authorization": "Bearer tok", "COOKIE": "x=1"}
    masked = mask_sensitive(headers)
    assert masked["Authorization"] == "***"
    assert masked["COOKIE"] == "***"


def test_mask_sensitive_leaves_others_intact() -> None:
    headers = {"x-request-id": "abc", "accept": "application/json"}
    assert mask_sensitive(headers) == headers
