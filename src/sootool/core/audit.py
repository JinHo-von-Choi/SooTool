from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sootool.core.result_types import Trace, TraceStep


def _normalize(v: Any) -> Any:
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (list, tuple)):
        return [_normalize(x) for x in v]
    if isinstance(v, dict):
        return {k: _normalize(x) for k, x in v.items()}
    return v


@dataclass
class CalcTrace:
    tool:         str
    formula:      str              = ""
    inputs:       dict[str, Any]   = field(default_factory=dict)
    steps:        list[TraceStep]  = field(default_factory=list)
    output_value: Any              = None

    def input(self, name: str, value: Any) -> None:
        self.inputs[name] = _normalize(value)

    def step(self, label: str, value: Any) -> None:
        self.steps.append({"label": label, "value": _normalize(value)})

    def output(self, value: Any) -> None:
        self.output_value = _normalize(value)

    def to_dict(self) -> Trace:
        return {
            "tool":    self.tool,
            "formula": self.formula,
            "inputs":  self.inputs,
            "steps":   self.steps,
            "output":  self.output_value,
        }


# ---------------------------------------------------------------------------
# Deterministic reproducibility stamp (ADR-021)
#
# integrity_stamp() produces a canonical-JSON sha256 of the tool inputs plus
# the policy metadata (if any) and the package version. The stamp is injected
# into _meta.integrity by the server post-processor, never mutating result or
# trace (ADR-011 invariant).
# ---------------------------------------------------------------------------


def _canonical_json(value: Any) -> str:
    """Return a canonical JSON representation used for hashing.

    Uses ``sort_keys=True`` and the most compact separators so that two
    semantically-equal input dicts (e.g. with keys in different order) produce
    an identical hash. ``default=str`` keeps Decimal and other non-JSON types
    stable by falling back to the same str() form used by trace normalization.
    """
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _IntegrityContext(threading.local):
    """Per-thread scratch pad for the in-flight tool invocation.

    ``inputs``         — kwargs captured at REGISTRY.invoke entry.
    ``policy_meta``    — set by policy loaders when a policy YAML is consumed.
    ``sootool_version``— cached package version (importlib.metadata lookup).
    """

    def __init__(self) -> None:
        super().__init__()
        self.inputs: dict[str, Any] | None = None
        self.policy_meta: dict[str, Any] | None = None


_INTEGRITY_CTX = _IntegrityContext()


def set_current_inputs(inputs: dict[str, Any] | None) -> None:
    """Record the current tool inputs for integrity stamping (thread-local)."""
    _INTEGRITY_CTX.inputs = dict(inputs) if inputs is not None else None


def set_policy_meta(
    source: str | None,
    sha256: str | None,
    domain: str | None = None,
    key: str | None = None,
    year: int | None = None,
    status: str | None = None,
    effective_from: str | None = None,
    effective_to: str | None = None,
) -> None:
    """Record policy metadata for the current tool invocation (thread-local).

    Multiple policy loads within a single tool call are allowed — the last one
    wins, matching the semantics of trace_ext.enrich_response which only
    stamps a single policy per response.
    """
    if sha256 is None and source is None:
        _INTEGRITY_CTX.policy_meta = None
        return
    meta: dict[str, Any] = {}
    if sha256 is not None:
        meta["policy_sha256"] = sha256
    if source is not None and domain is not None and key is not None and year is not None:
        meta["policy_source"] = f"{domain}/{key}/{year}"
    if status is not None:
        meta["policy_status"] = status
    if effective_from is not None:
        meta["policy_effective_from"] = effective_from
    if effective_to is not None:
        meta["policy_effective_to"] = effective_to
    _INTEGRITY_CTX.policy_meta = meta


def reset_integrity_ctx() -> None:
    """Clear the integrity context after a tool call completes."""
    _INTEGRITY_CTX.inputs = None
    _INTEGRITY_CTX.policy_meta = None


def _get_sootool_version() -> str:
    """Resolve the installed package version (cached per process)."""
    global _SOOTOOL_VERSION_CACHE
    if _SOOTOOL_VERSION_CACHE is not None:
        return _SOOTOOL_VERSION_CACHE
    try:
        from importlib.metadata import version
        _SOOTOOL_VERSION_CACHE = version("sootool")
    except Exception:  # PackageNotFoundError or anything unexpected
        _SOOTOOL_VERSION_CACHE = "0.0.0+unknown"
    return _SOOTOOL_VERSION_CACHE


_SOOTOOL_VERSION_CACHE: str | None = None


def _strip_meta(value: Any) -> Any:
    """모든 중첩 수준에서 ``_meta`` 키를 제거한다.

    _meta 에는 세션 통계, 힌트처럼 호출 이력에 따라 달라지는 값이 들어가므로 결과 해시에서 뺀다.
    """
    if isinstance(value, dict):
        return {k: _strip_meta(v) for k, v in value.items() if k != "_meta"}
    if isinstance(value, (list, tuple)):
        return [_strip_meta(v) for v in value]
    return value


def result_hash(result: dict[str, Any]) -> str:
    """응답 본문(result, trace 등)의 정규화 JSON sha256. ``_meta`` 는 제외한다."""
    return _sha256_hex(_canonical_json(_strip_meta(result)))


def integrity_stamp(
    tool_name:    str,
    tool_version: str,
    inputs:       dict[str, Any] | None,
    policy_meta:  dict[str, Any] | None = None,
    result:       dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the _meta.integrity block for a single tool response.

    Parameters
    ----------
    tool_name    : Fully qualified tool name (``namespace.name``).
    tool_version : Tool version string (``ToolEntry.version``).
    inputs       : Snapshot of kwargs passed to the tool; canonicalised and
                   sha256'd to produce ``input_hash``.
    policy_meta  : Optional dict with ``policy_sha256`` and ``policy_source``
                   keys, injected when the tool consumed a policy YAML.
    result       : Optional response body; when given, ``result_hash`` (sha256
                   of the canonical body without any ``_meta``) is added.

    Returns
    -------
    Dict with fixed key order suitable for direct assignment to
    ``response["_meta"]["integrity"]``.
    """
    canonical    = _canonical_json(inputs if inputs is not None else {})
    input_hash   = _sha256_hex(canonical)
    stamp: dict[str, Any] = {
        "tool":            tool_name,
        "input_hash":      input_hash,
    }
    if result is not None:
        stamp["result_hash"] = result_hash(result)
    stamp["tool_version"]    = tool_version
    stamp["sootool_version"] = _get_sootool_version()
    if policy_meta:
        sha = policy_meta.get("policy_sha256")
        src = policy_meta.get("policy_source")
        if sha is not None:
            stamp["policy_sha256"] = sha
        if src is not None:
            stamp["policy_source"] = src
        for extra in ("policy_status", "policy_effective_from", "policy_effective_to"):
            if policy_meta.get(extra) is not None:
                stamp[extra] = policy_meta[extra]
    return stamp
