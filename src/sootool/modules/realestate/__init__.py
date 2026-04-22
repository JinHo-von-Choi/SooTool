"""Real estate domain module.

Importing this package registers all real estate tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.realestate import (
    acquisition_tax,
    ratios,
    rental_yield,
    transfer_tax,
)

__all__ = ["ratios", "acquisition_tax", "transfer_tax", "rental_yield"]
