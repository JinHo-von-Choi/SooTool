"""Korean real estate acquisition tax (취득세) calculator.

Author: 최진호
Date: 2026-04-22

Policy reference: kr_acquisition_{year}.yaml
- 지방세법 제11조 (취득세)
- 주택 취득세율: 6억 이하 1%, 6~9억 2%, 9억 초과 3%
- 다주택 중과세: 2주택(규제지역) 8%, 3주택 이상 12%
- 농어촌특별세 0.2% (전용면적 85m² 초과)
- 지방교육세 0.1%
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
from sootool.policies import load as policy_load


def _lookup_bracket_rate(price: Decimal, brackets: list[dict[str, Any]]) -> Decimal:
    """Look up base tax rate from bracket table."""
    for bracket in brackets:
        upper = bracket["upper"]
        if upper is None or price <= D(str(upper)):
            return D(str(bracket["rate"]))
    # Fallback to last bracket
    return D(str(brackets[-1]["rate"]))


def _surcharge_rate(
    house_count:  int,
    is_regulated: bool,
    surcharge_data: dict[str, Any],
) -> Decimal:
    """Determine multi-house surcharge rate."""
    if house_count >= 3:
        return D(str(surcharge_data["three_plus"]))
    if house_count == 2 and is_regulated:
        return D(str(surcharge_data["two_houses_regulated"]))
    if house_count == 2 and not is_regulated:
        return D(str(surcharge_data["two_houses_non_regulated"]))
    return Decimal("0")


@REGISTRY.tool(
    namespace="realestate",
    name="kr_acquisition_tax",
    description=(
        "한국 주택 취득세 계산. "
        "지방세법 제11조 기준 (취득가액, 주택 수, 규제지역, 면적). "
        "농어촌특별세 및 지방교육세 포함."
    ),
    version="1.0.0",
)
def realestate_kr_acquisition_tax(
    price:        str,
    house_count:  int,
    is_regulated: bool,
    area_m2:      str,
    year:         int,
) -> dict[str, Any]:
    """Calculate Korean housing acquisition tax.

    Args:
        price:        취득가액 (원, Decimal string)
        house_count:  취득 후 보유 주택 수
        is_regulated: 규제지역 여부
        area_m2:      전용면적 (m², Decimal string) — 농특세 부과 기준
        year:         과세 기준 연도

    Returns:
        {base_tax: str, surcharges: dict, total_tax: str, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_acquisition_tax",
        formula=(
            "base_tax = price * base_rate; "
            "surcharge_tax = price * surcharge_rate; "
            "rural_tax = price * rural_rate (if area > 85m²); "
            "edu_tax = price * local_edu_rate; "
            "total = base_tax + surcharge_tax + rural_tax + edu_tax"
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
    brackets       = house_data["brackets"]
    surcharge_data = house_data["multi_house_surcharge"]
    surcharge_info = data["surcharges"]

    trace.input("price",        price)
    trace.input("house_count",  house_count)
    trace.input("is_regulated", is_regulated)
    trace.input("area_m2",      area_m2)
    trace.input("year",         year)

    base_rate     = _lookup_bracket_rate(p, brackets)
    s_rate        = _surcharge_rate(house_count, is_regulated, surcharge_data)
    rural_rate    = D(str(surcharge_info["rural_special"])) if area > D("85") else Decimal("0")
    edu_rate      = D(str(surcharge_info["local_edu"]))

    base_tax      = round_apply(p * base_rate,  0, RoundingPolicy.FLOOR)
    surcharge_tax = round_apply(p * s_rate,      0, RoundingPolicy.FLOOR)
    rural_tax     = round_apply(p * rural_rate,  0, RoundingPolicy.FLOOR)
    edu_tax       = round_apply(p * edu_rate,    0, RoundingPolicy.FLOOR)
    total_tax     = base_tax + surcharge_tax + rural_tax + edu_tax

    surcharges = {
        "multi_house_surcharge": str(surcharge_tax),
        "rural_special":         str(rural_tax),
        "local_edu":             str(edu_tax),
    }

    trace.step("base_rate",     str(base_rate))
    trace.step("surcharge_rate", str(s_rate))
    trace.step("rural_rate",    str(rural_rate))
    trace.step("edu_rate",      str(edu_rate))
    trace.step("base_tax",      str(base_tax))
    trace.step("surcharges",    str(surcharges))
    trace.output(str(total_tax))

    return {
        "base_tax":       str(base_tax),
        "surcharges":     surcharges,
        "total_tax":      str(total_tax),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
