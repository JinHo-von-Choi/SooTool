"""Stats domain module.

Importing this package registers all stats tools in REGISTRY.

Internal dtype: float64 (numpy/scipy/statsmodels).
Boundary casting: Decimal strings via sootool.core.cast.
See README.md for full dtype and casting policy.
"""
from __future__ import annotations

from sootool.modules.stats import (
    anova,
    bootstrap,
    ci,
    descriptive,
    effect_size,
    inference,
    nonparametric,
    regression,
)

__all__ = [
    "descriptive",
    "inference",
    "ci",
    "regression",
    "anova",
    "nonparametric",
    "bootstrap",
    "effect_size",
]
