"""Korean local (광역자치단체) property tax differentiation.

Author: 최진호
Date: 2026-04-24

광역자치단체별 취득세·재산세 차등 계산기. 지방세법 제11조·제111조의
표준세율을 기준으로 하되, 각 광역 시·도세 조례로 정해지는 감면·중과
계수를 적용한다. 지방세법 제6조는 지방자치단체가 표준세율의 50% 범위에서
가감 조정할 수 있도록 허용한다.

지원 광역 (9):
  seoul, gyeonggi, busan, incheon, daegu, daejeon, gwangju, ulsan, sejong

mode:
  - "acquisition": 취득세 (기본 브래킷 × 광역계수 + 부가세)
  - "property":    재산세 (공시가 × 공정시장가액비율 × 누진세율 × 광역계수 + 지방교육세 + 도시지역분)
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

_SUPPORTED_REGIONS: set[str] = {
    "seoul",
    "gyeonggi",
    "busan",
    "incheon",
    "daegu",
    "daejeon",
    "gwangju",
    "ulsan",
    "sejong",
}

_VALID_MODES: set[str] = {"acquisition", "property"}


def _lookup_bracket_rate(price: Decimal, brackets: list[dict[str, Any]]) -> Decimal:
    """취득세 단일 구간(flat) 요율 검색. 가격이 속한 첫 구간의 rate 반환."""
    for bracket in brackets:
        upper = bracket["upper"]
        if upper is None or price <= D(str(upper)):
            return D(str(bracket["rate"]))
    return D(str(brackets[-1]["rate"]))


@REGISTRY.tool(
    namespace="realestate",
    name="kr_local_property",
    description=(
        "광역자치단체별 취득세·재산세 차등 계산. "
        "지방세법 제6조 탄력세율을 광역 조례 계수로 반영. "
        "지원: seoul/gyeonggi/busan/incheon/daegu/daejeon/gwangju/ulsan/sejong."
    ),
    version="1.0.0",
)
def realestate_kr_local_property(
    region:          str,
    mode:            str,
    price:           str,
    year:            int,
    area_m2:         str   = "0",
    include_urban:   bool  = True,
) -> dict[str, Any]:
    """Calculate acquisition or property tax with region-specific coefficient.

    Args:
        region:        광역자치단체 코드 (seoul/gyeonggi/busan/...).
        mode:          "acquisition" 또는 "property".
        price:         취득가액(acquisition) 또는 공시가격(property), 원.
        year:          과세연도.
        area_m2:       전용면적(m²) — acquisition 모드에서 농특세 판정 기준.
        include_urban: property 모드에서 도시지역분 포함 여부.

    Returns:
        {region, mode, coefficient, base_tax, surcharges, total_tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_local_property",
        formula=(
            "acquisition: base = price * bracket_rate * region_coef; "
            "surcharges = price * (rural + local_edu); total = base + surcharges. "
            "property: taxable = price * fair_market_ratio; "
            "base = progressive(taxable) * region_coef; "
            "total = base + local_edu(20%) + urban(0.14% if applicable)."
        ),
    )

    if region not in _SUPPORTED_REGIONS:
        raise InvalidInputError(
            f"region은 {sorted(_SUPPORTED_REGIONS)} 중 하나여야 합니다."
        )
    if mode not in _VALID_MODES:
        raise InvalidInputError(
            f"mode는 {sorted(_VALID_MODES)} 중 하나여야 합니다."
        )

    p    = D(price)
    area = D(area_m2)

    if p <= Decimal("0"):
        raise InvalidInputError("price는 0보다 커야 합니다.")
    if area < Decimal("0"):
        raise InvalidInputError("area_m2는 0 이상이어야 합니다.")

    policy_doc = policy_load("realestate", "kr_local_property", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("region",        region)
    trace.input("mode",          mode)
    trace.input("price",         price)
    trace.input("area_m2",       area_m2)
    trace.input("year",          year)
    trace.input("include_urban", include_urban)

    surcharges_cfg = data["surcharges"]

    if mode == "acquisition":
        coef     = D(str(data["acquisition_coefficient"][region]))
        brackets = data["acquisition_brackets"]

        base_rate    = _lookup_bracket_rate(p, brackets)
        effective    = base_rate * coef
        base_tax     = round_apply(p * effective, 0, RoundingPolicy.FLOOR)

        rural_rate   = D(str(surcharges_cfg["rural_special"])) if area > D("85") else Decimal("0")
        edu_rate     = D(str(surcharges_cfg["acq_local_edu"]))
        rural_tax    = round_apply(p * rural_rate, 0, RoundingPolicy.FLOOR)
        edu_tax      = round_apply(p * edu_rate,   0, RoundingPolicy.FLOOR)
        total_tax    = base_tax + rural_tax + edu_tax

        surcharges   = {
            "rural_special": str(rural_tax),
            "local_edu":     str(edu_tax),
        }

        trace.step("region_coefficient", str(coef))
        trace.step("base_rate",          str(base_rate))
        trace.step("effective_rate",     str(effective))
        trace.step("base_tax",           str(base_tax))
        trace.step("surcharges",         surcharges)
        trace.output(str(total_tax))

        resp: dict[str, Any] = {
            "region":         region,
            "mode":           mode,
            "coefficient":    str(coef),
            "base_tax":       str(base_tax),
            "surcharges":     surcharges,
            "total_tax":      str(total_tax),
            "policy_version": pv,
            "trace":          trace.to_dict(),
        }
        return enrich_response(resp, policy_doc)

    # mode == "property"
    coef     = D(str(data["property_coefficient"][region]))
    brackets = data["property_brackets"]
    fmr      = D(str(data["fair_market_ratio"]))
    taxable  = p * fmr

    raw_tax, _eff, _marg, breakdown = _calc_progressive(
        taxable, brackets, RoundingPolicy.HALF_UP, 0
    )
    # 광역 계수 적용 후 소수 절사
    base_tax = round_apply(raw_tax * coef, 0, RoundingPolicy.FLOOR)

    local_edu_rate = D(str(surcharges_cfg["local_edu_rate"]))
    urban_rate     = D(str(surcharges_cfg["urban_area_rate"]))

    local_edu = round_apply(base_tax * local_edu_rate, 0, RoundingPolicy.FLOOR)

    urban_applicable = bool(data["urban_area_applicable"][region])
    if include_urban and urban_applicable:
        urban = round_apply(taxable * urban_rate, 0, RoundingPolicy.FLOOR)
    else:
        urban = Decimal("0")

    total_tax = base_tax + local_edu + urban

    surcharges = {
        "local_edu":  str(local_edu),
        "urban_area": str(urban),
    }

    trace.step("region_coefficient", str(coef))
    trace.step("taxable_base",       str(taxable))
    trace.step("raw_property_tax",   str(raw_tax))
    trace.step("breakdown",          breakdown)
    trace.step("base_tax",           str(base_tax))
    trace.step("urban_applicable",   urban_applicable)
    trace.step("surcharges",         surcharges)
    trace.output(str(total_tax))

    resp = {
        "region":         region,
        "mode":           mode,
        "coefficient":    str(coef),
        "taxable_base":   str(taxable),
        "base_tax":       str(base_tax),
        "surcharges":     surcharges,
        "total_tax":      str(total_tax),
        "breakdown":      breakdown,
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
