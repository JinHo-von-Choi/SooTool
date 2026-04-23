"""Payroll domain module.

Importing this package registers all payroll tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.payroll import (
    hourly_to_monthly_net,
    kr_bonus_tax,
    kr_salary,
    kr_severance_pay,
    kr_year_end_tax_settlement,
)

__all__ = [
    "kr_salary",
    "kr_severance_pay",
    "kr_year_end_tax_settlement",
    "kr_bonus_tax",
    "hourly_to_monthly_net",
]
