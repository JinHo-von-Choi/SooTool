from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


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
        self._tools: dict[str, ToolEntry] = {}

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

    def invoke(self, full_name: str, **kwargs: Any) -> Any:
        if full_name not in self._tools:
            raise KeyError(full_name)
        return self._tools[full_name].fn(**kwargs)


REGISTRY = ToolRegistry()
