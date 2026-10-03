"""근로자 부담 건강보험료와 장기요양보험료 산정(급여 실수령액과 연말 정산이 함께 쓴다).

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.decimal_ops import D
from sootool.core.rounding import RoundingPolicy, truncate_to_unit
from sootool.core.rounding import apply as round_apply


def truncate_premium(value: Decimal, unit: Decimal) -> Decimal:
    """보험료를 unit 원 단위로 절사한다. 비율의 자릿수 한계로 생기는 미소 오차는 먼저 정리한다."""
    return truncate_to_unit(round_apply(value, 6, RoundingPolicy.HALF_UP), unit)


def employee_health_premium(remuneration_monthly: Decimal, hi_cfg: dict[str, Any]) -> tuple[Decimal, Decimal]:
    """근로자 부담 보수월액 건강보험료와 장기요양보험료. 월별 보험료 상·하한의 근로자 부담분으로 제한한다."""
    employee_rate = D(str(hi_cfg["employee_rate"]))
    share         = employee_rate / (employee_rate + D(str(hi_cfg["employer_rate"])))
    unit          = D(str(hi_cfg.get("premium_truncation_unit", 1)))
    health        = truncate_premium(remuneration_monthly * employee_rate, unit)
    if hi_cfg.get("premium_min_monthly_total") is not None:
        health = max(health, truncate_premium(D(str(hi_cfg["premium_min_monthly_total"])) * share, unit))
    if hi_cfg.get("premium_max_monthly_total") is not None:
        health = min(health, truncate_premium(D(str(hi_cfg["premium_max_monthly_total"])) * share, unit))
    long_term_care = truncate_premium(health * D(str(hi_cfg["long_term_care_rate_of_health"])), unit)
    return health, long_term_care
