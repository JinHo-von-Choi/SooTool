"""Transfer tax adapter for real estate: delegates to tax.capital_gains_kr.

Author: 최진호
Date: 2026-04-22

This module is a thin adapter over the existing tax.capital_gains_kr tool,
adding real estate-specific metadata (domain, policy context).
"""
from __future__ import annotations

from typing import Any, TypedDict, cast

from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult


class TransferTaxRateCandidate(TypedDict):
    """세율별 산출세액 후보. rate 는 적용 세율의 이름."""

    rate: str
    tax:  str


class RealestateKrTransferTaxResult(PolicyResult):
    gain:                 str
    exempt:               bool
    taxable_portion_gain: str
    ltct_rate:            str
    ltct_deduction:       str
    taxable_gain:         str
    basic_deduction:      str
    tax_base:             str
    applied_rate:         str | None
    rate_candidates:      list[TransferTaxRateCandidate]
    tax:                  str
    domain:               str
    module:               str


@REGISTRY.tool(
    namespace="realestate",
    name="kr_transfer_tax",
    description=(
        "한국 부동산 양도소득세를 tax.capital_gains_kr 에 위임해 계산하고 domain, module 표식을 붙인다. "
        "금액은 원 단위 문자열, 세액은 decimals 자리 HALF_UP 반올림. is_one_house=true 는 주택(1세대 1주택 "
        "비과세·고가주택 안분·보유 거주 공제), false 는 주택 외 토지·건물로 처리한다. 오용 예: 다주택 "
        "주택 양도에 false 입력(중과·분양권·미등기는 tax.capital_gains_kr 직접 사용)."
    ),
    version="1.0.0",
    policy=True,
)
def realestate_kr_transfer_tax(
    acquisition_price: str,
    sale_price:        str,
    holding_years:     int,
    is_one_house:      bool,
    year:              int,
    decimals:          int = 0,
) -> RealestateKrTransferTaxResult:
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

    return cast(RealestateKrTransferTaxResult, result)
