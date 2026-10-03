"""Korean automobile tax (자동차 소유에 대한 자동차세) for passenger cars.

Author: 최진호
Date: 2026-10-03

지방세법 제127조제1항제1호~제3호, 제128조제3항, 제151조제1항제7호:
  승용자동차 연세액 A = 배기량(cc) × 시시당 세액(배기량 구간 단일 세율)
  비영업용 승용 차령 n >= 3: 각 기분세액 = A/2 - (A/2 × 5%) × (min(n, 12) - 2)
  그 밖의 승용자동차(전기 등): 연세액 정액
  연세액 일시 신고납부: 공제액 = 공제 대상 세액(시행령 제125조제3항) × 이자율(시행령 제125조제6항)
  지방교육세: 비영업용 승용 자동차세액 × 30%
  끝수: 징수 단위마다 10원 미만 버림 (지방세기본법 제59조, 국고금 관리법 제47조)

모델링 범위:
  - 승용자동차(제1호·제3호)만 다룬다. 승합·화물·특수·3륜 이하 소형자동차는 다루지 않는다.
  - 1년 전체 보유를 가정한다. 신규등록·이전·말소에 따른 일할계산(법 제129조·제130조)은 하지 않는다.
  - 표준세율만 적용한다. 조례에 따른 세율 조정(법 제127조제3항, 제151조제2항)과 감면은 반영하지 않는다.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any, NotRequired, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_VEHICLE_TYPES   = ("passenger", "other_passenger")
_ANNUAL_PAYMENTS = ("none", "january", "march", "june", "september")


class VehicleTaxResult(PolicyResult):
    vehicle_type:                str
    business_use:                bool
    base_annual_tax:             str
    first_half_tax:              str
    second_half_tax:             str
    annual_vehicle_tax:          str
    annual_payment:              str
    annual_payment_deduction:    str
    vehicle_tax_payable:         str
    local_education_tax_applies: bool
    local_education_tax:         str
    total_payable:               str
    displacement_cc:             NotRequired[int]
    per_cc_rate:                 NotRequired[str]
    vehicle_age_first_half:      NotRequired[int]
    vehicle_age_second_half:     NotRequired[int]


def _truncate(value: Decimal, unit: Decimal) -> Decimal:
    """unit 원 미만 끝수를 버린다."""
    return round_apply(value / unit, 0, RoundingPolicy.DOWN) * unit


def _per_cc_rate(cc: int, table: list[dict[str, Any]]) -> Decimal:
    """배기량이 속한 구간(상한 포함)의 시시당 세액. 구간 세율을 배기량 전체에 적용한다."""
    for row in table:
        upper = row.get("upper_cc")
        if upper is None or cc <= int(upper):
            return D(str(row["per_cc"]))
    return D(str(table[-1]["per_cc"]))


def _vehicle_ages(start: date, year: int) -> tuple[int, int]:
    """시행령 제122조제2항의 제1기분·제2기분 차령."""
    if start.month <= 6:
        age = year - start.year + 1
        return age, age
    return year - start.year, year - start.year + 1


def _period_tax(half: Decimal, age: int, cfg: dict[str, Any], unit: Decimal) -> Decimal:
    """비영업용 승용자동차 기분세액. 차령이 최소 차령 미만이면 경감하지 않는다."""
    if age < int(cfg["min_age"]):
        return _truncate(half, unit)
    n         = min(age, int(cfg["max_age"]))
    reduction = half * D(str(cfg["rate_per_year"])) * Decimal(n - int(cfg["base_age"]))
    return _truncate(half - reduction, unit)


def _deduction_base(
    period:      str,
    year:        int,
    annual:      Decimal,
    second_half: Decimal,
    half_days:   int,
) -> Decimal:
    """연세액 일시 신고납부 공제 대상 세액 (법 제128조제3항 표, 시행령 제125조제3항)."""
    year_end  = date(year, 12, 31)
    year_days = Decimal(366 if calendar.isleap(year) else 365)
    if period == "january":
        return annual * Decimal((year_end - date(year, 1, 31)).days) / year_days
    if period == "march":
        return annual * Decimal((year_end - date(year, 3, 31)).days) / year_days
    if period == "june":
        return second_half
    return second_half * Decimal((year_end - date(year, 9, 30)).days) / Decimal(half_days)


@REGISTRY.tool(
    namespace="tax",
    name="kr_vehicle_tax",
    description=(
        "한국 승용자동차 자동차세 연세액과 지방교육세(비영업용 30%)를 계산한다(지방세법 제127조, 제128조, 제151조). "
        "배기량은 cc 정수, 차령기산일은 YYYY-MM-DD(보통 최초 신규등록일)이다. 비영업용은 차령 3년부터 연 5%, 최대 50% 경감하고 "
        "annual_payment 로 1월, 3월, 6월, 9월 연납 공제(이자율 5%)를 적용한다. 세액은 기분마다 10원 미만 버림. "
        "승합, 화물, 특수차, 신규등록 일할계산, 조례 세율 조정은 다루지 않으며, 차령을 연식 차이로 넣으면 기산일 규칙과 어긋난다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_vehicle_tax(
    year:            int,
    vehicle_type:    str        = "passenger",
    displacement_cc: int | None = None,
    business_use:    bool       = False,
    age_start_date:  str | None = None,
    annual_payment:  str        = "none",
) -> VehicleTaxResult:
    """Calculate annual automobile tax for a passenger car.

    Args:
        year:            과세연도.
        vehicle_type:    passenger(배기량 기준 승용, 법 제127조제1항제1호) 또는
                         other_passenger(전기·태양열·알코올 승용, 같은 항 제3호).
        displacement_cc: 배기량(cc, 양의 정수). passenger 이면 필수.
        business_use:    영업용 여부(시행령 제122조제1항). 기본 비영업용.
        age_start_date:  차령기산일(YYYY-MM-DD, 자동차관리법 시행령 제3조). 비영업용 passenger 이면 필수.
        annual_payment:  연세액 일시 신고납부 시기. none/january/march/june/september.

    Returns:
        {vehicle_type, business_use, displacement_cc, per_cc_rate, base_annual_tax,
         vehicle_age_first_half, vehicle_age_second_half, first_half_tax, second_half_tax,
         annual_vehicle_tax, annual_payment, annual_payment_deduction, vehicle_tax_payable,
         local_education_tax_applies, local_education_tax, total_payable, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_vehicle_tax",
        formula=(
            "A = 배기량 × 시시당 세액; 비영업용 차령 n>=3 기분세액 = A/2 - (A/2 × 5%)(min(n,12) - 2); "
            "연납 공제 = 공제 대상 세액 × 이자율; 지방교육세 = 비영업용 승용 자동차세 × 30%; "
            "징수 단위마다 10원 미만 버림"
        ),
    )

    if vehicle_type not in _VEHICLE_TYPES:
        raise InvalidInputError(f"vehicle_type은 {list(_VEHICLE_TYPES)} 중 하나여야 합니다.")
    if annual_payment not in _ANNUAL_PAYMENTS:
        raise InvalidInputError(f"annual_payment는 {list(_ANNUAL_PAYMENTS)} 중 하나여야 합니다.")

    start: date | None = None
    if age_start_date is not None:
        try:
            start = date.fromisoformat(age_start_date)
        except ValueError as exc:
            raise InvalidInputError(
                f"age_start_date 형식 오류: {age_start_date!r} (YYYY-MM-DD 필요)"
            ) from exc
        if start.year > year:
            raise InvalidInputError("age_start_date는 과세연도 말일 이전이어야 합니다.")

    if vehicle_type == "passenger":
        if isinstance(displacement_cc, bool) or not isinstance(displacement_cc, int) or displacement_cc <= 0:
            raise InvalidInputError("passenger 는 displacement_cc(양의 정수 cc)가 필요합니다.")
        if not business_use and start is None:
            raise InvalidInputError("비영업용 passenger 는 차령 경감 판정을 위해 age_start_date가 필요합니다.")

    policy_doc = policy_load("tax", "kr_vehicle_tax", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]
    unit       = D(str(data["rounding_unit"]))
    usage      = "business" if business_use else "non_business"

    trace.input("year",            year)
    trace.input("vehicle_type",    vehicle_type)
    trace.input("displacement_cc", displacement_cc)
    trace.input("business_use",    business_use)
    trace.input("age_start_date",  age_start_date)
    trace.input("annual_payment",  annual_payment)

    resp: dict[str, Any] = {"vehicle_type": vehicle_type, "business_use": business_use}

    if vehicle_type == "passenger":
        assert displacement_cc is not None
        rate        = _per_cc_rate(displacement_cc, data["passenger_cc_rates"][usage])
        base_annual = Decimal(displacement_cc) * rate
        half        = base_annual / Decimal("2")
        resp["displacement_cc"] = displacement_cc
        resp["per_cc_rate"]     = str(rate)
        trace.step("per_cc_rate", str(rate))
        if business_use:
            first_half  = _truncate(half, unit)
            second_half = _truncate(half, unit)
        else:
            assert start is not None
            age_1, age_2 = _vehicle_ages(start, year)
            first_half   = _period_tax(half, age_1, data["age_reduction"], unit)
            second_half  = _period_tax(half, age_2, data["age_reduction"], unit)
            resp["vehicle_age_first_half"]  = age_1
            resp["vehicle_age_second_half"] = age_2
            trace.step("vehicle_age_first_half",  age_1)
            trace.step("vehicle_age_second_half", age_2)
    else:
        base_annual = D(str(data["other_passenger_annual"][usage]))
        first_half  = _truncate(base_annual / Decimal("2"), unit)
        second_half = _truncate(base_annual / Decimal("2"), unit)

    annual        = first_half + second_half
    edu_applies   = not business_use
    edu_rate      = D(str(data["local_education_tax_rate"]))
    pay_cfg       = data["annual_payment"]

    if annual_payment == "none":
        payable = annual
        edu_tax = (
            _truncate(first_half * edu_rate, unit) + _truncate(second_half * edu_rate, unit)
            if edu_applies else Decimal("0")
        )
    else:
        target   = _deduction_base(annual_payment, year, annual, second_half, int(pay_cfg["second_half_days"]))
        rate_cap = min(D(str(pay_cfg["interest_rate"])), D(str(pay_cfg["max_ratio"])))
        payable  = _truncate(annual - target * rate_cap, unit)
        edu_tax  = _truncate(payable * edu_rate, unit) if edu_applies else Decimal("0")
        trace.step("deduction_target_tax", str(target))
        trace.step("deduction_rate",       str(rate_cap))

    deduction = annual - payable
    total     = payable + edu_tax

    trace.step("base_annual_tax",          str(base_annual))
    trace.step("first_half_tax",           str(first_half))
    trace.step("second_half_tax",          str(second_half))
    trace.step("annual_vehicle_tax",       str(annual))
    trace.step("annual_payment_deduction", str(deduction))
    trace.step("local_education_tax",      str(edu_tax))
    trace.output(str(total))

    resp.update({
        "base_annual_tax":             str(base_annual),
        "first_half_tax":              str(first_half),
        "second_half_tax":             str(second_half),
        "annual_vehicle_tax":          str(annual),
        "annual_payment":              annual_payment,
        "annual_payment_deduction":    str(deduction),
        "vehicle_tax_payable":         str(payable),
        "local_education_tax_applies": edu_applies,
        "local_education_tax":         str(edu_tax),
        "total_payable":               str(total),
        "policy_version":              pv,
        "trace":                       trace.to_dict(),
    })
    return cast(VehicleTaxResult, enrich_response(resp, policy_doc))
