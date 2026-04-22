"""Accounting domain module.

Importing this package registers all accounting tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.accounting import bookkeeping, depreciation, vat

__all__ = ["bookkeeping", "depreciation", "vat"]
