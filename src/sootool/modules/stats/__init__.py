"""Stats domain module.

Importing this package registers all stats tools in REGISTRY.

Internal dtype: float64 (numpy/scipy/statsmodels).
Boundary casting: Decimal strings via sootool.core.cast.
See README.md for full dtype and casting policy.
"""
from __future__ import annotations

from sootool.modules.stats import (
    ci,
    descriptive,
    inference,
    regression,
)

__all__ = ["descriptive", "inference", "ci", "regression"]
