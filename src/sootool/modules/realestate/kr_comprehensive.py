"""Korean comprehensive real-estate holding tax (종합부동산세, 종부세법 §8~§9).

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


@REGISTRY.tool(
    namespace="realestate",
    name="kr_comprehensive",
    description=(
        "종합부동산세 계산 (종부세법 §8~§9). 공제 후 공정시장가액비율 적용, "
        "1주택/다주택 누진세율 산출, 농어촌특별세 20% 합산."
    ),
    version="1.0.0",
)
def realestate_kr_comprehensive(
    total_published_price: str,
    year:                  int,
    house_count:           int,
) -> dict[str, Any]:
    """Calculate comprehensive real-estate tax (종부세).

    Args:
        total_published_price: 보유 주택 공시가격 합계 (원)
        year:                  과세연도
        house_count:           보유 주택 수 (1, 2, 3+ 구간 분기)

    Returns:
        {taxable_base, base_tax, rural_tax, total_tax, breakdown,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_comprehensive",
        formula=(
            "과세표준 = (공시가격 합계 - 기본공제) × 공정시장가액비율; "
            "종부세 = 누진세율(과세표준); "
            "농어촌특별세 = 종부세 × 20%"
        ),
    )

    pp = D(total_published_price)
    if pp <= Decimal("0"):
        raise InvalidInputError("total_published_price는 0보다 커야 합니다.")
    if house_count < 1:
        raise InvalidInputError("house_count는 1 이상이어야 합니다.")

    policy_doc = policy_load("realestate", "kr_comprehensive", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("total_published_price", total_published_price)
    trace.input("year",                  year)
    trace.input("house_count",           house_count)

    is_one_house = (house_count == 1)
    base_dedu_cfg = data["base_deduction"]
    deduction = (
        D(str(base_dedu_cfg["one_house"])) if is_one_house
        else D(str(base_dedu_cfg["multi_house"]))
    )

    after_deduct = pp - deduction
    if after_deduct <= Decimal("0"):
        trace.step("deduction",     str(deduction))
        trace.step("after_deduct",  str(after_deduct))
        trace.output("0")
        resp = {
            "published_price": str(pp),
            "deduction":       str(deduction),
            "taxable_base":    "0",
            "base_tax":        "0",
            "rural_tax":       "0",
            "total_tax":       "0",
            "breakdown":       [],
            "policy_version":  pv,
            "trace":           trace.to_dict(),
        }
        return enrich_response(resp, policy_doc)

    fmr_ratio = D(str(data["fair_market_ratio"]))
    taxable   = after_deduct * fmr_ratio

    brackets = (
        data["one_house_brackets"] if is_one_house
        else data["multi_house_brackets"]
    )

    base_tax, _eff, _m, breakdown = _calc_progressive(
        taxable, brackets, RoundingPolicy.HALF_UP, 0
    )

    rural_rate = D(str(data["rural_special_rate"]))
    rural_tax  = round_apply(base_tax * rural_rate, 0, RoundingPolicy.FLOOR)

    total = base_tax + rural_tax

    trace.step("deduction",    str(deduction))
    trace.step("taxable_base", str(taxable))
    trace.step("breakdown",    breakdown)
    trace.step("rural_tax",    str(rural_tax))
    trace.output(str(total))

    resp = {
        "published_price": str(pp),
        "deduction":       str(deduction),
        "taxable_base":    str(taxable),
        "base_tax":        str(base_tax),
        "rural_tax":       str(rural_tax),
        "total_tax":       str(total),
        "breakdown":       breakdown,
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
