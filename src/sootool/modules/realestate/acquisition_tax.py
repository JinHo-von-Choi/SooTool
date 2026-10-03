"""Korean real estate acquisition tax (취득세) calculator.

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

Policy reference: kr_acquisition_{year}.yaml
- 지방세법 제11조제1항제8호 (주택 유상취득 표준세율)
  6억 이하 1%, 6억 초과 9억 이하 (가액×2/3억원-3)×1/100, 9억 초과 3%
- 지방세법 제13조의2 (중과세율, 표준세율을 대체)
  조정 2주택·비조정 3주택 8%, 조정 3주택 이상·비조정 4주택 이상·법인 12%
- 농어촌특별세법 제5조제1항제6호: 표준세율 적용분 0.2%, 중과 0.6%/1.0% (전용 85m² 초과)
- 지방세법 제151조제1항제1호: 지방교육세 = 표준세율의 10%, 중과 0.4%
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
from sootool.modules.realestate._kr_local_tax import acquisition_standard_rate
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_NATIONAL_HOUSING_AREA_M2 = Decimal("85")


class AcquisitionSurcharges(TypedDict):
    """취득세 본세 외 부가분. 모두 원 단위 문자열."""

    multi_house_surcharge: str
    rural_special:         str
    local_edu:             str


class RealestateKrAcquisitionTaxResult(PolicyResult):
    standard_rate:   str
    applied_rate:    str
    heavy_applied:   bool
    acquisition_tax: str
    base_tax:        str
    surcharges:      AcquisitionSurcharges
    total_tax:       str


def _optional_rate(surcharge_data: dict[str, Any], key: str, fallback: str | None = None) -> Decimal | None:
    """중과세율 키를 읽는다. 값이 없거나 0이면 중과 없음(None)."""
    raw = surcharge_data.get(key)
    if raw is None and fallback is not None:
        raw = surcharge_data.get(fallback)
    if raw is None:
        return None
    rate = D(str(raw))
    return rate if rate > Decimal("0") else None


def _heavy_rate(
    house_count:       int,
    is_regulated:      bool,
    is_corporate:      bool,
    is_heavy_excluded: bool,
    surcharge_data:    dict[str, Any],
) -> Decimal | None:
    """지방세법 제13조의2제1항의 중과세율. 중과 대상이 아니면 None."""
    if is_heavy_excluded:
        return None
    if is_corporate:
        return _optional_rate(surcharge_data, "corporate")
    if is_regulated:
        if house_count >= 3:
            return _optional_rate(surcharge_data, "three_plus")
        if house_count == 2:
            return _optional_rate(surcharge_data, "two_houses_regulated")
        return None
    if house_count >= 4:
        return _optional_rate(surcharge_data, "four_plus_non_regulated", "three_plus")
    if house_count == 3:
        return _optional_rate(surcharge_data, "three_houses_non_regulated", "three_plus")
    if house_count == 2:
        return _optional_rate(surcharge_data, "two_houses_non_regulated")
    return None


def _heavy_row(heavy_rate: Decimal, surcharge_info: dict[str, Any]) -> dict[str, Any]:
    for row in surcharge_info.get("heavy", []):
        if D(str(row["rate"])) == heavy_rate:
            return dict(row)
    raise InvalidInputError(f"정책에 중과세율 {heavy_rate}의 부가세 정의가 없습니다.")


@REGISTRY.tool(
    namespace="realestate",
    name="kr_acquisition_tax",
    description=(
        "한국 주택 유상취득 취득세와 농어촌특별세·지방교육세를 계산한다. 표준세율은 6억 이하 1%, "
        "6억 초과 9억 이하 산식 세율, 9억 초과 3%이고, 조정 2주택·비조정 3주택 8%, 조정 3주택 이상·"
        "비조정 4주택 이상·법인 12% 중과세율이 표준세율을 대체한다. 금액은 원 단위 문자열, 세목별 "
        "원 미만 절사. 농어촌특별세는 전용 85㎡ 초과만 과세. 오용 예: house_count 에 취득 전 주택 수 입력."
    ),
    version="1.1.0",
    policy=True,
)
def realestate_kr_acquisition_tax(
    price:             str,
    house_count:       int,
    is_regulated:      bool,
    area_m2:           str,
    year:              int,
    is_corporate:      bool = False,
    is_heavy_excluded: bool = False,
) -> RealestateKrAcquisitionTaxResult:
    """Calculate Korean housing acquisition tax.

    Args:
        price:             취득가액 (원, Decimal string)
        house_count:       취득 후 1세대 보유 주택 수 (입주권·분양권·주거용 오피스텔 포함은 호출자 판정)
        is_regulated:      취득 주택이 조정대상지역에 있는지 여부
        area_m2:           전용면적 (m², Decimal string). 85m² 이하는 농어촌특별세 비과세
        year:              과세 기준 연도
        is_corporate:      법인(법인 아닌 사단·재단 포함) 취득 여부
        is_heavy_excluded: 중과 제외 주택(일시적 2주택, 지방세법 시행령 제28조의2 주택 등) 여부

    Returns:
        {standard_rate, applied_rate, heavy_applied, acquisition_tax, base_tax, surcharges,
         total_tax, policy_version, trace}. base_tax 는 표준세율분, surcharges.multi_house_surcharge 는
         중과세율로 늘어난 몫이며 둘의 합이 취득세 본세다.
    """
    trace = CalcTrace(
        tool="realestate.kr_acquisition_tax",
        formula=(
            "applied_rate = heavy_rate if 중과 else standard_rate; "
            "acquisition_tax = price * applied_rate; "
            "base_tax = price * standard_rate; surcharge = acquisition_tax - base_tax; "
            "rural_tax = price * rural_rate (area > 85m²); "
            "edu_tax = price * (standard_rate * 10% | heavy 0.4%); "
            "total = acquisition_tax + rural_tax + edu_tax"
        ),
    )

    p    = D(price)
    area = D(area_m2)

    if p <= Decimal("0"):
        raise InvalidInputError("price는 0보다 커야 합니다.")
    if area < Decimal("0"):
        raise InvalidInputError("area_m2는 0 이상이어야 합니다.")
    if house_count < 1:
        raise InvalidInputError("house_count는 1 이상이어야 합니다.")

    policy_doc = policy_load("realestate", "kr_acquisition", year)
    data = policy_doc["data"]
    pv   = policy_doc["policy_version"]

    house_data     = data["house"]
    surcharge_data = house_data["multi_house_surcharge"]
    surcharge_info = data["surcharges"]

    trace.input("price",             price)
    trace.input("house_count",       house_count)
    trace.input("is_regulated",      is_regulated)
    trace.input("area_m2",           area_m2)
    trace.input("year",              year)
    trace.input("is_corporate",      is_corporate)
    trace.input("is_heavy_excluded", is_heavy_excluded)

    standard_rate = acquisition_standard_rate(p, house_data["brackets"])
    heavy_rate    = _heavy_rate(house_count, is_regulated, is_corporate, is_heavy_excluded, surcharge_data)
    applied_rate  = heavy_rate if heavy_rate is not None else standard_rate
    large_area    = area > _NATIONAL_HOUSING_AREA_M2

    if heavy_rate is not None:
        row        = _heavy_row(heavy_rate, surcharge_info)
        rural_rate = D(str(row["rural_special"])) if large_area else Decimal("0")
        edu_rate   = D(str(row["local_edu"]))
    else:
        rural_rate = D(str(surcharge_info["rural_special"])) if large_area else Decimal("0")
        ratio      = surcharge_info.get("local_edu_ratio_of_rate")
        edu_rate   = (
            standard_rate * D(str(ratio)) if ratio is not None
            else D(str(surcharge_info["local_edu"]))
        )

    acquisition_tax = round_apply(p * applied_rate,  0, RoundingPolicy.FLOOR)
    base_tax        = round_apply(p * standard_rate, 0, RoundingPolicy.FLOOR)
    surcharge_tax   = max(acquisition_tax - base_tax, Decimal("0"))
    rural_tax       = round_apply(p * rural_rate,    0, RoundingPolicy.FLOOR)
    edu_tax         = round_apply(p * edu_rate,      0, RoundingPolicy.FLOOR)
    total_tax       = base_tax + surcharge_tax + rural_tax + edu_tax

    surcharges = {
        "multi_house_surcharge": str(surcharge_tax),
        "rural_special":         str(rural_tax),
        "local_edu":             str(edu_tax),
    }

    trace.step("standard_rate",   str(standard_rate))
    trace.step("heavy_rate",      str(heavy_rate) if heavy_rate is not None else None)
    trace.step("applied_rate",    str(applied_rate))
    trace.step("rural_rate",      str(rural_rate))
    trace.step("edu_rate",        str(edu_rate))
    trace.step("acquisition_tax", str(acquisition_tax))
    trace.step("base_tax",        str(base_tax))
    trace.step("surcharges",      str(surcharges))
    trace.output(str(total_tax))

    resp: dict[str, Any] = {
        "standard_rate":   str(standard_rate),
        "applied_rate":    str(applied_rate),
        "heavy_applied":   heavy_rate is not None,
        "acquisition_tax": str(acquisition_tax),
        "base_tax":        str(base_tax),
        "surcharges":      surcharges,
        "total_tax":       str(total_tax),
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
    return cast(RealestateKrAcquisitionTaxResult, enrich_response(resp, policy_doc))
