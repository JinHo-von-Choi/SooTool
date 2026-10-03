"""근로소득세액공제와 표준세액공제 산식(연말정산과 종합소득세 신고 흐름이 함께 쓴다).

상수(비율, 구간, 한도)는 ``kr_withholding`` 정책의 ``labor_income_tax_credit``, ``standard_tax_credit`` 에 있다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from sootool.core.decimal_ops import D


def standard_tax_credit(policy_data: Mapping[str, Any]) -> Decimal:
    """표준세액공제(제59조의4제9항제1호)."""
    return D(str(policy_data["standard_tax_credit"]))


def labor_income_tax_credit_limit(total_salary: Decimal, cfg: Mapping[str, Any]) -> Decimal:
    """근로소득세액공제 한도(소득세법 제59조제2항, 총급여액 구간별)."""
    for tier in cfg["limits"]:
        if tier["upper"] is None or total_salary <= D(str(tier["upper"])):
            reduced = D(str(tier["base"])) - (total_salary - D(str(tier["over"]))) * D(str(tier["rate"]))
            return max(reduced, D(str(tier["floor"])))
    raise ValueError("labor_income_tax_credit.limits 의 마지막 구간은 upper: null 이어야 합니다.")


def labor_income_tax_credit(computed_tax: Decimal, total_salary: Decimal, policy_data: Mapping[str, Any]) -> Decimal:
    """근로소득세액공제(소득세법 제59조제1항, 제2항)."""
    cfg       = policy_data["labor_income_tax_credit"]
    threshold = D(str(cfg["low_threshold"]))
    if computed_tax <= threshold:
        credit = computed_tax * D(str(cfg["low_rate"]))
    else:
        credit = D(str(cfg["base"])) + (computed_tax - threshold) * D(str(cfg["high_rate"]))
    return min(credit, labor_income_tax_credit_limit(total_salary, cfg))
