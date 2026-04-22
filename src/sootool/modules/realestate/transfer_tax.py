"""Transfer tax adapter for real estate: delegates to tax.capital_gains_kr.

Author: 최진호
Date: 2026-04-22

This module is a thin adapter over the existing tax.capital_gains_kr tool,
adding real estate-specific metadata (domain, policy context).
"""
from __future__ import annotations

from typing import Any

from sootool.core.registry import REGISTRY


@REGISTRY.tool(
    namespace="realestate",
    name="kr_transfer_tax",
    description=(
        "한국 부동산 양도소득세 계산. "
        "tax.capital_gains_kr에 위임하며 부동산 도메인 메타데이터 추가."
    ),
    version="1.0.0",
)
def realestate_kr_transfer_tax(
    acquisition_price: str,
    sale_price:        str,
    holding_years:     int,
    is_one_house:      bool,
    year:              int,
    decimals:          int = 0,
) -> dict[str, Any]:
    """Calculate Korean real estate transfer tax (양도소득세).

    Delegates computation to tax.capital_gains_kr and appends
    realestate-specific metadata.

    Args:
        acquisition_price: 취득가액 (원, Decimal string)
        sale_price:        양도가액 (원, Decimal string)
        holding_years:     보유 기간 (년, 정수)
        is_one_house:      1세대1주택 여부
        year:              과세연도
        decimals:          소수점 자리수 (기본 0)

    Returns:
        All fields from tax.capital_gains_kr, plus {domain, module}
    """
    result: dict[str, Any] = REGISTRY.invoke(
        "tax.capital_gains_kr",
        acquisition_price=acquisition_price,
        sale_price=sale_price,
        holding_years=holding_years,
        is_one_house=is_one_house,
        year=year,
        decimals=decimals,
    )

    # Append realestate domain metadata
    result["domain"] = "realestate"
    result["module"] = "realestate.kr_transfer_tax"

    return result
