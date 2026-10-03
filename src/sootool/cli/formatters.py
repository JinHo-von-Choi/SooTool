"""CLI 출력 형식: json, pretty, raw, trace. 도구 결과의 수치는 가공하지 않는다."""
from __future__ import annotations

import json
from typing import Any

FORMATS = ("pretty", "json", "raw", "trace")
_PREVIEW_CHARS = 160


def _dump(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(value, ensure_ascii=False, indent=indent, default=str, sort_keys=False)


def _preview(value: Any) -> str:
    if isinstance(value, str):
        return value
    text = _dump(value)
    return text if len(text) <= _PREVIEW_CHARS else text[: _PREVIEW_CHARS - 1] + "…"


def format_result(result: Any, fmt: str) -> str:
    """결과를 지정한 형식의 문자열로 만든다."""
    if not isinstance(result, dict):
        return _dump(result, indent=2)
    if fmt == "json":
        return _dump(result, indent=2)
    if fmt == "trace":
        return _dump(result.get("trace", {}), indent=2)
    if fmt == "raw":
        return _dump({k: v for k, v in result.items() if k not in ("trace", "_meta")}, indent=2)

    lines = [f"{key}: {_preview(value)}" for key, value in result.items() if key not in ("trace", "_meta")]
    trace = result.get("trace")
    if isinstance(trace, dict):
        if trace.get("formula"):
            lines.append(f"-- formula: {trace['formula']}")
        for index, step in enumerate(trace.get("steps", []), start=1):
            lines.append(f"-- step {index}. {step.get('label', '')}: {_preview(step.get('value'))}")
    integrity = (result.get("_meta") or {}).get("integrity")
    if isinstance(integrity, dict):
        lines.append(
            f"-- receipt: input {str(integrity.get('input_hash', ''))[:12]} "
            f"result {str(integrity.get('result_hash', ''))[:12]} engine {(result.get('_meta') or {}).get('engine', '')}"
        )
    return "\n".join(lines)


def format_error(payload: dict[str, Any]) -> str:
    return _dump({"error": payload}, indent=2)
