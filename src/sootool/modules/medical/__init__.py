"""Medical domain module.

Importing this package registers all medical tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.medical import (
    body,
    dose,
    egfr,
    pregnancy,
)

__all__ = ["body", "dose", "egfr", "pregnancy"]
