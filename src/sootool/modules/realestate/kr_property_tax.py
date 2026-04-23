"""Korean property tax (재산세, 지방세법 제111조).

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
    name="kr_property_tax",
    description=(
        "한국 주택 재산세(지방세법 §111) 계산. 공시가액 × 공정시장가액비율(60%) "
        "→ 누진세율 적용 후 지방교육세·도시지역분 합산."
    ),
    version="1.0.0",
)
def realestate_kr_property_tax(
    published_price: str,
    year:            int,
    include_urban:   bool = True,
) -> dict[str, Any]:
    """Calculate Korean property tax.

    Args:
        published_price: 공시가격 (원)
        year:            과세연도
        include_urban:   도시지역분(0.14%) 합산 여부

    Returns:
        {published_price, taxable_base, property_tax, surcharges, total_tax,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_property_tax",
        formula=(
            "과세표준 = 공시가격 × 공정시장가액비율; "
            "재산세 = 누진세율(과세표준); "
            "지방교육세 = 재산세 × 20%; "
            "도시지역분 = 과세표준 × 0.14% (옵션)"
        ),
    )

    pp = D(published_price)
    if pp <= Decimal("0"):
        raise InvalidInputError("published_price는 0보다 커야 합니다.")

    policy_doc = policy_load("realestate", "kr_property_tax", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("published_price", published_price)
    trace.input("year",            year)
    trace.input("include_urban",   include_urban)

    fmr_ratio   = D(str(data["fair_market_ratio"]))
    taxable     = pp * fmr_ratio

    property_tax, _eff, _m, breakdown = _calc_progressive(
        taxable, data["brackets"], RoundingPolicy.HALF_UP, 0
    )

    surcharges_cfg = data["surcharges"]
    local_edu_rate = D(str(surcharges_cfg["local_edu_rate"]))
    urban_rate     = D(str(surcharges_cfg["urban_area_rate"]))

    local_edu = round_apply(property_tax * local_edu_rate, 0, RoundingPolicy.FLOOR)
    urban     = round_apply(taxable * urban_rate, 0, RoundingPolicy.FLOOR) if include_urban else Decimal("0")

    total = property_tax + local_edu + urban

    surcharges = {
        "local_edu":    str(local_edu),
        "urban_area":   str(urban),
    }

    trace.step("taxable_base", str(taxable))
    trace.step("property_tax", str(property_tax))
    trace.step("breakdown",    breakdown)
    trace.step("surcharges",   surcharges)
    trace.output(str(total))

    resp = {
        "published_price": str(pp),
        "taxable_base":    str(taxable),
        "property_tax":    str(property_tax),
        "surcharges":      surcharges,
        "total_tax":       str(total),
        "breakdown":       breakdown,
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
