"""Payroll domain module.

Importing this package registers all payroll tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.payroll import (
    hourly_to_monthly_net,
    kr_bonus_tax,
    kr_donation_deduction,
    kr_education_deduction,
    kr_gross_from_net,
    kr_health_income_premium,
    kr_housing_loan_deduction,
    kr_medical_deduction,
    kr_minimum_wage_check,
    kr_national_pension_benefit,
    kr_overtime_pay,
    kr_salary,
    kr_severance_pay,
    kr_weekly_holiday_pay,
    kr_year_end_tax_settlement,
)

__all__ = [
    "kr_salary",
    "kr_gross_from_net",
    "kr_severance_pay",
    "kr_year_end_tax_settlement",
    "kr_bonus_tax",
    "hourly_to_monthly_net",
    "kr_medical_deduction",
    "kr_education_deduction",
    "kr_donation_deduction",
    "kr_housing_loan_deduction",
    "kr_overtime_pay",
    "kr_weekly_holiday_pay",
    "kr_minimum_wage_check",
    "kr_national_pension_benefit",
    "kr_health_income_premium",
]
