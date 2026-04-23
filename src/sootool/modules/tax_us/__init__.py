"""US tax domain module (tax_us namespace).

Importing this package registers all US tax tools in REGISTRY.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from sootool.modules.tax_us import (
    capital_gains,
    federal_income,
    state_tax,
)

__all__ = [
    "federal_income",
    "capital_gains",
    "state_tax",
]
