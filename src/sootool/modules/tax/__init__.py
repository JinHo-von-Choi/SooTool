"""Tax domain module.

Importing this package registers all tax tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.tax import (
    capital_gains,
    kr_comprehensive_income_tax,
    kr_corporate,
    kr_education_tax_add,
    kr_eitc,
    kr_gift,
    kr_income,
    kr_inheritance,
    kr_local_income_tax,
    kr_pension_income,
    kr_registration_license_tax,
    kr_rural_special_tax,
    kr_securities_transaction,
    kr_simplified_vat,
    kr_vehicle_tax,
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
    "kr_local_income_tax",
    "kr_education_tax_add",
    "kr_rural_special_tax",
    "kr_simplified_vat",
    "kr_eitc",
    "kr_vehicle_tax",
    "kr_registration_license_tax",
    "kr_securities_transaction",
    "kr_pension_income",
    "kr_comprehensive_income_tax",
]
