from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("sootool.core.registry")

PostProcessor = Callable[[dict[str, Any], str], dict[str, Any]]


@dataclass
class ToolEntry:
    namespace:   str
    name:        str
    description: str
    fn:          Callable[..., Any]
    version:     str                = "1.0.0"
    deprecated:  dict[str, Any] | None = None

    @property
    def full_name(self) -> str:
        return f"{self.namespace}.{self.name}"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools:           dict[str, ToolEntry]  = {}
        self._post_processors: list[PostProcessor]   = []

    def tool(
        self,
        *,
        namespace:   str,
        name:        str,
        description: str       = "",
        version:     str       = "1.0.0",
        deprecated:  dict[str, Any] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            entry = ToolEntry(
                namespace=namespace,
                name=name,
                description=description,
                fn=fn,
                version=version,
                deprecated=deprecated,
            )
            if entry.full_name in self._tools:
                raise ValueError(f"도구 중복 등록: {entry.full_name}")
            self._tools[entry.full_name] = entry
            return fn

        return deco

    def list(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def register_post_processor(self, fn: PostProcessor) -> None:
        """Register a post-processor applied to every invoke() result.

        Post-processors are called only when the result is a dict containing
        a "trace" key (ADR-011: result/trace are never modified; processors
        must write exclusively to _meta).

        Signature: fn(response: dict, tool_name: str) -> dict
        """
        self._post_processors.append(fn)

    def invoke(self, full_name: str, **kwargs: Any) -> Any:
        if full_name not in self._tools:
            raise KeyError(full_name)
        # Capture the inputs for the integrity stamp before the tool runs and
        # restore the previous context on exit. Stack-style save/restore is
        # required because batch/pipeline tools recursively invoke() other
        # tools — a naive reset would clobber the outer frame's context.
        from sootool.core.audit import _INTEGRITY_CTX, set_current_inputs
        prev_inputs = _INTEGRITY_CTX.inputs
        prev_policy = _INTEGRITY_CTX.policy_meta
        set_current_inputs(kwargs)
        # Each nested call starts with a fresh policy slot; the previous
        # frame's policy is restored in the finally block below.
        _INTEGRITY_CTX.policy_meta = None
        try:
            result = self._tools[full_name].fn(**kwargs)
            if isinstance(result, dict) and "trace" in result:
                for proc in self._post_processors:
                    try:
                        result = proc(result, full_name)
                    except Exception:
                        log.warning(
                            "Post-processor %s failed for %s", proc, full_name, exc_info=True
                        )
            return result
        finally:
            _INTEGRITY_CTX.inputs = prev_inputs
            _INTEGRITY_CTX.policy_meta = prev_policy


REGISTRY = ToolRegistry()
