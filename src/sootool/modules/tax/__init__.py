"""Tax domain module.

Importing this package registers all tax tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.tax import (
    capital_gains,
    kr_corporate,
    kr_gift,
    kr_income,
    kr_inheritance,
    kr_withholding,
    progressive,
)

__all__ = [
    "progressive",
    "kr_income",
    "kr_withholding",
    "capital_gains",
    "kr_corporate",
    "kr_inheritance",
    "kr_gift",
]
