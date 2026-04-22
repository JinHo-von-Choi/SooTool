from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


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
    steps:        list[dict[str, Any]] = field(default_factory=list)
    output_value: Any              = None

    def input(self, name: str, value: Any) -> None:
        self.inputs[name] = _normalize(value)

    def step(self, label: str, value: Any) -> None:
        self.steps.append({"label": label, "value": _normalize(value)})

    def output(self, value: Any) -> None:
        self.output_value = _normalize(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool":    self.tool,
            "formula": self.formula,
            "inputs":  self.inputs,
            "steps":   self.steps,
            "output":  self.output_value,
        }
