"""Real estate domain module.

Importing this package registers all real estate tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.realestate import (
    acquisition_tax,
    kr_comprehensive,
    kr_local_property,
    kr_property_tax,
    kr_subscription_score,
    ratios,
    rental_yield,
    transfer_tax,
)

__all__ = [
    "ratios",
    "acquisition_tax",
    "transfer_tax",
    "rental_yield",
    "kr_property_tax",
    "kr_comprehensive",
    "kr_local_property",
    "kr_subscription_score",
]
