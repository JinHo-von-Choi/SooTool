"""Korean property tax (재산세, 지방세법 제110조·제111조·제111조의2).

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03

- 과세표준 = 시가표준액 × 공정시장가액비율 (1세대 1주택은 시가표준액 구간별 비율)
- 과세표준상한액(제110조제3항): 직전 연도 시가표준액이 주어지면 적용
- 세율: 표준세율 누진, 시가표준액 9억 이하 1세대 1주택은 특례세율(제111조의2)
- 지방교육세 = 재산세의 20%, 도시지역분 = 과세표준의 0.14%(선택)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.realestate._kr_local_tax import (
    property_fair_market_ratio,
    property_special_brackets,
    property_tax_base,
)
from sootool.modules.tax.progressive import BracketBreakdown, _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class PropertyTaxSurcharges(TypedDict):
    """재산세 부가분. 원 단위 문자열."""

    local_edu:  str
    urban_area: str


class RealestateKrPropertyTaxResult(PolicyResult):
    published_price:      str
    fair_market_ratio:    str
    taxable_base:         str
    tax_base_cap:         str | None
    special_rate_applied: bool
    property_tax:         str
    surcharges:           PropertyTaxSurcharges
    total_tax:            str
    breakdown:            list[BracketBreakdown]


@REGISTRY.tool(
    namespace="realestate",
    name="kr_property_tax",
    description=(
        "한국 주택 재산세(지방세법 §110~§111의2)와 지방교육세·도시지역분을 계산한다. 공시가격(원)에 "
        "공정시장가액비율(일반 60%, 1세대 1주택은 시가표준액 구간별)을 곱해 과세표준을 구하고, 직전 연도 "
        "공시가격을 주면 과세표준상한을 적용한다. 누진세율, 9억 이하 1세대 1주택은 특례세율. 재산세는 원 "
        "미만 반올림, 부가분은 절사. 오용 예: 토지·건축물에 사용."
    ),
    version="1.1.0",
    policy=True,
)
def realestate_kr_property_tax(
    published_price:            str,
    year:                       int,
    include_urban:              bool       = True,
    is_one_house:               bool       = False,
    prior_year_published_price: str | None = None,
) -> RealestateKrPropertyTaxResult:
    """Calculate Korean property tax.

    Args:
        published_price:            공시가격(시가표준액, 원)
        year:                       과세연도
        include_urban:              도시지역분(0.14%) 합산 여부
        is_one_house:               1세대 1주택(지방세법 시행령 제110조의2) 여부
        prior_year_published_price: 직전 연도 시가표준액(원). 주어지면 과세표준상한액을 적용

    Returns:
        {published_price, fair_market_ratio, taxable_base, tax_base_cap, special_rate_applied,
         property_tax, surcharges, total_tax, breakdown, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_property_tax",
        formula=(
            "과세표준 = min(공시가격 × 공정시장가액비율, 과세표준상한액); "
            "재산세 = 누진세율(과세표준) (1세대 1주택 9억 이하 특례세율); "
            "지방교육세 = 재산세 × 20%; "
            "도시지역분 = 과세표준 × 0.14% (옵션)"
        ),
    )

    pp = D(published_price)
    if pp <= Decimal("0"):
        raise InvalidInputError("published_price는 0보다 커야 합니다.")
    prior = D(prior_year_published_price) if prior_year_published_price is not None else None
    if prior is not None and prior <= Decimal("0"):
        raise InvalidInputError("prior_year_published_price는 0보다 커야 합니다.")

    policy_doc = policy_load("realestate", "kr_property_tax", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("published_price",            published_price)
    trace.input("year",                       year)
    trace.input("include_urban",              include_urban)
    trace.input("is_one_house",               is_one_house)
    trace.input("prior_year_published_price", prior_year_published_price)

    fmr_ratio = property_fair_market_ratio(pp, data, is_one_house)
    cap_rate  = D(str(data["tax_base_cap_rate"])) if data.get("tax_base_cap_rate") is not None else None
    taxable, base_cap = property_tax_base(pp, fmr_ratio, prior, cap_rate)

    special  = property_special_brackets(pp, data, is_one_house)
    brackets = special if special is not None else data["brackets"]

    property_tax, _eff, _m, breakdown = _calc_progressive(
        taxable, brackets, RoundingPolicy.HALF_UP, 0
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

    trace.step("fair_market_ratio",    str(fmr_ratio))
    trace.step("tax_base_cap",         str(base_cap) if base_cap is not None else None)
    trace.step("taxable_base",         str(taxable))
    trace.step("special_rate_applied", special is not None)
    trace.step("property_tax",         str(property_tax))
    trace.step("breakdown",            breakdown)
    trace.step("surcharges",           surcharges)
    trace.output(str(total))

    resp: dict[str, Any] = {
        "published_price":      str(pp),
        "fair_market_ratio":    str(fmr_ratio),
        "taxable_base":         str(taxable),
        "tax_base_cap":         str(base_cap) if base_cap is not None else None,
        "special_rate_applied": special is not None,
        "property_tax":         str(property_tax),
        "surcharges":           surcharges,
        "total_tax":            str(total),
        "breakdown":            breakdown,
        "policy_version":       pv,
        "trace":                trace.to_dict(),
    }
    return cast(RealestateKrPropertyTaxResult, enrich_response(resp, policy_doc))
