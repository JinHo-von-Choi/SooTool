"""근로소득세액공제와 표준세액공제 상수와 산식(연말정산과 종합소득세 신고 흐름이 함께 쓴다).

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

from decimal import Decimal

STANDARD_TAX_CREDIT = Decimal("130000")

# 근로소득세액공제 (소득세법 제59조제1항)
_LABOR_CREDIT_THRESHOLD = Decimal("1300000")
_LABOR_CREDIT_LOW_RATE  = Decimal("0.55")
_LABOR_CREDIT_BASE      = Decimal("715000")
_LABOR_CREDIT_HIGH_RATE = Decimal("0.30")


def _labor_income_tax_credit_limit(total_salary: Decimal) -> Decimal:
    """근로소득세액공제 한도 (소득세법 제59조제2항, 총급여액 구간별)."""
    if total_salary <= Decimal("33000000"):
        return Decimal("740000")
    if total_salary <= Decimal("70000000"):
        limit = Decimal("740000") - (total_salary - Decimal("33000000")) * Decimal("8") / Decimal("1000")
        return max(limit, Decimal("660000"))
    if total_salary <= Decimal("120000000"):
        limit = Decimal("660000") - (total_salary - Decimal("70000000")) / Decimal("2")
        return max(limit, Decimal("500000"))
    limit = Decimal("500000") - (total_salary - Decimal("120000000")) / Decimal("2")
    return max(limit, Decimal("200000"))


def _labor_income_tax_credit(computed_tax: Decimal, total_salary: Decimal) -> Decimal:
    """근로소득세액공제 (소득세법 제59조제1항·제2항)."""
    if computed_tax <= _LABOR_CREDIT_THRESHOLD:
        credit = computed_tax * _LABOR_CREDIT_LOW_RATE
    else:
        credit = _LABOR_CREDIT_BASE + (computed_tax - _LABOR_CREDIT_THRESHOLD) * _LABOR_CREDIT_HIGH_RATE
    return min(credit, _labor_income_tax_credit_limit(total_salary))
