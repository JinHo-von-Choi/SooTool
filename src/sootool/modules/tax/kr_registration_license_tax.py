"""Korean registration license tax (등록에 대한 등록면허세) on real estate registrations.

Author: 최진호
Date: 2026-10-03

지방세법 제28조제1항제1호 다목·라목·마목, 같은 항 단서, 제151조제1항제2호:
  정률 등기: 등록면허세 = 과세표준 × 1천분의 2, 산출세액이 6천원 미만이면 6천원
  그 밖의 등기: 건당 6천원
  지방교육세 = 등록면허세 × 20%
  끝수: 10원 미만 버림 (지방세기본법 제59조, 국고금 관리법 제47조)

모델링 범위:
  - 부동산 등기 중 소유권 외의 물권과 임차권의 설정·이전(다목), 경매신청·가압류·가처분·가등기(라목),
    그 밖의 등기(마목)만 다룬다.
  - 소유권 보존·이전 등기(가목·나목)는 다루지 않는다. 취득을 원인으로 하는 등기는 등록에서 제외되어
    취득세로 과세되며(법 제23조제1호), 같은 호 단서의 예외 등기도 이 도구의 범위 밖이다.
  - 표준세율만 적용한다. 조례에 따른 가감(법 제28조제6항, 제151조제2항)과 감면은 반영하지 않는다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_OTHER = "other"


class RegistrationLicenseTaxResult(PolicyResult):
    registration_type:   str
    tax_base:            str
    tax_base_kind:       str
    rate:                str
    computed_tax:        str
    minimum_applied:     bool
    registration_tax:    str
    local_education_tax: str
    total_tax:           str


def _truncate(value: Decimal, unit: Decimal) -> Decimal:
    """unit 원 미만 끝수를 버린다."""
    return round_apply(value / unit, 0, RoundingPolicy.DOWN) * unit


@REGISTRY.tool(
    namespace="tax",
    name="kr_registration_license_tax",
    description=(
        "부동산 등기의 등록면허세와 지방교육세(20%)를 계산한다(지방세법 제28조제1항제1호, 제151조). "
        "저당권, 전세권, 지상권, 지역권, 임차권, 경매신청, 가압류, 가처분, 가등기는 과세표준(원 문자열) × 2/1000, "
        "6천원 미만이면 6천원이고 other 는 건당 6천원이다. 세액은 10원 미만 버림. 소유권 보존과 이전 등기는 취득세로 "
        "과세되므로 다루지 않는다. 임차권 과세표준을 보증금으로 넣는 것은 오용이며 월 임대차금액을 넣는다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_registration_license_tax(
    registration_type: str,
    year:              int,
    tax_base:          str | None = None,
) -> RegistrationLicenseTaxResult:
    """Calculate registration license tax on a real estate registration.

    Args:
        registration_type: superficies(지상권), mortgage(저당권), servitude(지역권), jeonse(전세권),
                           lease(임차권), auction(경매신청), provisional_attachment(가압류),
                           provisional_disposition(가처분), provisional_registration(가등기),
                           other(그 밖의 등기, 건당 정액).
        year:              과세연도.
        tax_base:          과세표준(원). other 외에는 필수. 종류는 결과의 tax_base_kind 참조.

    Returns:
        {registration_type, tax_base, tax_base_kind, rate, computed_tax, minimum_applied,
         registration_tax, local_education_tax, total_tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_registration_license_tax",
        formula=(
            "등록면허세 = max(과세표준 × 세율, 6천원) (그 밖의 등기는 건당 6천원); "
            "지방교육세 = 등록면허세 × 20%; 10원 미만 버림"
        ),
    )

    policy_doc = policy_load("tax", "kr_registration_license_tax", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]
    rates: dict[str, Any] = data["real_estate_rates"]
    allowed    = [*rates.keys(), _OTHER]

    if registration_type not in allowed:
        raise InvalidInputError(f"registration_type은 {allowed} 중 하나여야 합니다.")

    trace.input("registration_type", registration_type)
    trace.input("year",              year)
    trace.input("tax_base",          tax_base)

    unit    = D(str(data["rounding_unit"]))
    flat    = D(str(data["other_registration_flat"]))
    edu_pct = D(str(data["local_education_tax_rate"]))

    if registration_type == _OTHER:
        base      = Decimal("0")
        base_kind = "건당 정액"
        rate      = Decimal("0")
        computed  = flat
        minimum   = False
        reg_tax   = flat
    else:
        if tax_base is None:
            raise InvalidInputError(f"{registration_type} 는 tax_base(과세표준, 원)가 필요합니다.")
        base = D(tax_base)
        if base <= Decimal("0"):
            raise InvalidInputError("tax_base는 0보다 커야 합니다.")
        base_kind = str(rates[registration_type]["base"])
        rate      = D(str(rates[registration_type]["rate"]))
        computed  = base * rate
        minimum   = computed < flat
        reg_tax   = flat if minimum else _truncate(computed, unit)

    edu_tax = _truncate(reg_tax * edu_pct, unit)
    total   = reg_tax + edu_tax

    trace.step("rate",                str(rate))
    trace.step("computed_tax",        str(computed))
    trace.step("minimum_applied",     minimum)
    trace.step("registration_tax",    str(reg_tax))
    trace.step("local_education_tax", str(edu_tax))
    trace.output(str(total))

    resp: dict[str, Any] = {
        "registration_type":   registration_type,
        "tax_base":            str(base),
        "tax_base_kind":       base_kind,
        "rate":                str(rate),
        "computed_tax":        str(computed),
        "minimum_applied":     minimum,
        "registration_tax":    str(reg_tax),
        "local_education_tax": str(edu_tax),
        "total_tax":           str(total),
        "policy_version":      pv,
        "trace":               trace.to_dict(),
    }
    return cast(RegistrationLicenseTaxResult, enrich_response(resp, policy_doc))
