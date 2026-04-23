"""DSR, LTV, DTI ratio calculators for Korean real estate.

Author: 최진호
Date: 2026-04-22

Policy reference: kr_dsr_ltv_{year}.yaml
- DSR cap: 40% (금융위원회)
- LTV limits by area type and house count
- DTI limits by regulated/non-regulated area
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
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


@REGISTRY.tool(
    namespace="realestate",
    name="kr_dsr",
    description=(
        "DSR(총부채원리금상환비율) 계산. "
        "DSR = 연간 원리금 상환액 / 연간 소득. "
        "금융위원회 DSR 40% cap 기준."
    ),
    version="1.0.0",
)
def realestate_kr_dsr(
    annual_debt_payment: str,
    annual_income:       str,
    year:                int,
) -> dict[str, Any]:
    """Calculate DSR ratio.

    Args:
        annual_debt_payment: 연간 원리금 상환 총액 (원, Decimal string)
        annual_income:       연간 소득 (원, Decimal string)
        year:                적용 기준 연도

    Returns:
        {dsr: str, within_cap: bool, cap: str, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_dsr",
        formula="DSR = annual_debt_payment / annual_income",
    )

    debt   = D(annual_debt_payment)
    income = D(annual_income)

    if debt < Decimal("0"):
        raise InvalidInputError("annual_debt_payment는 0 이상이어야 합니다.")
    if income <= Decimal("0"):
        raise InvalidInputError("annual_income은 0보다 커야 합니다.")

    policy_doc = policy_load("realestate", "kr_dsr_ltv", year)
    data = policy_doc["data"]
    pv   = policy_doc["policy_version"]

    cap_rate = D(str(data["dsr_cap"]))

    trace.input("annual_debt_payment", annual_debt_payment)
    trace.input("annual_income",       annual_income)
    trace.input("year",                year)

    dsr_raw   = debt / income
    dsr       = round_apply(dsr_raw, 4, RoundingPolicy.HALF_EVEN)
    within_cap = dsr <= cap_rate

    trace.step("dsr_raw",    str(dsr_raw))
    trace.step("cap",        str(cap_rate))
    trace.step("within_cap", str(within_cap))
    trace.output(str(dsr))

    resp = {
        "dsr":            str(dsr),
        "within_cap":     within_cap,
        "cap":            str(cap_rate),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)


@REGISTRY.tool(
    namespace="realestate",
    name="kr_ltv",
    description=(
        "LTV(주택담보대출비율) 계산 및 한도 산출. "
        "규제지역/비규제지역, 주택 수에 따른 한도 적용."
    ),
    version="1.0.0",
)
def realestate_kr_ltv(
    loan_amount:     str,
    property_value:  str,
    year:            int,
    is_regulated:    bool,
    house_count:     int,
) -> dict[str, Any]:
    """Calculate LTV ratio and check against policy cap.

    Args:
        loan_amount:    대출액 (원, Decimal string)
        property_value: 주택가액 (원, Decimal string)
        year:           적용 기준 연도
        is_regulated:   규제지역 여부
        house_count:    보유 주택 수 (대출 후 기준)

    Returns:
        {ltv: str, within_cap: bool, max_loan: str, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_ltv",
        formula="LTV = loan_amount / property_value; max_loan = property_value * ltv_cap",
    )

    loan  = D(loan_amount)
    value = D(property_value)

    if loan < Decimal("0"):
        raise InvalidInputError("loan_amount는 0 이상이어야 합니다.")
    if value <= Decimal("0"):
        raise InvalidInputError("property_value는 0보다 커야 합니다.")
    if house_count < 1:
        raise InvalidInputError("house_count는 1 이상이어야 합니다.")

    policy_doc = policy_load("realestate", "kr_dsr_ltv", year)
    data = policy_doc["data"]
    pv   = policy_doc["policy_version"]
    ltv_data = data["ltv"]

    # Determine applicable LTV cap
    if is_regulated:
        if house_count >= 2:
            cap_rate = D(str(ltv_data["regulated_multi_house"]))
        else:
            cap_rate = D(str(ltv_data["regulated_first_house"]))
    else:
        if house_count >= 2:
            cap_rate = D(str(ltv_data["non_regulated_multi_house"]))
        else:
            cap_rate = D(str(ltv_data["non_regulated_first_house"]))

    trace.input("loan_amount",    loan_amount)
    trace.input("property_value", property_value)
    trace.input("is_regulated",   is_regulated)
    trace.input("house_count",    house_count)
    trace.input("year",           year)

    max_loan  = round_apply(value * cap_rate, 0, RoundingPolicy.FLOOR)
    ltv_raw   = loan / value
    ltv       = round_apply(ltv_raw, 4, RoundingPolicy.HALF_EVEN)
    # Use unrounded ratio for cap check to detect any excess (e.g. cap=0, loan>0)
    within_cap = ltv_raw <= cap_rate

    trace.step("cap_rate",   str(cap_rate))
    trace.step("max_loan",   str(max_loan))
    trace.step("ltv_raw",    str(ltv_raw))
    trace.step("within_cap", str(within_cap))
    trace.output(str(ltv))

    resp = {
        "ltv":            str(ltv),
        "within_cap":     within_cap,
        "max_loan":       str(max_loan),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)


@REGISTRY.tool(
    namespace="realestate",
    name="kr_dti",
    description=(
        "DTI(총부채상환비율) 계산. "
        "DTI = 월 원리금 상환액 / 월 소득. "
        "규제지역 40%, 비규제지역 60% cap."
    ),
    version="1.0.0",
)
def realestate_kr_dti(
    monthly_debt_payment: str,
    monthly_income:       str,
    year:                 int,
    is_regulated:         bool,
) -> dict[str, Any]:
    """Calculate DTI ratio.

    Args:
        monthly_debt_payment: 월 원리금 상환액 (원, Decimal string)
        monthly_income:       월 소득 (원, Decimal string)
        year:                 적용 기준 연도
        is_regulated:         규제지역 여부

    Returns:
        {dti: str, within_cap: bool, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_dti",
        formula="DTI = monthly_debt_payment / monthly_income",
    )

    payment = D(monthly_debt_payment)
    income  = D(monthly_income)

    if payment < Decimal("0"):
        raise InvalidInputError("monthly_debt_payment는 0 이상이어야 합니다.")
    if income <= Decimal("0"):
        raise InvalidInputError("monthly_income은 0보다 커야 합니다.")

    policy_doc = policy_load("realestate", "kr_dsr_ltv", year)
    data = policy_doc["data"]
    pv   = policy_doc["policy_version"]
    dti_data = data["dti"]

    cap_rate = D(str(
        dti_data["regulated"] if is_regulated else dti_data["non_regulated"]
    ))

    trace.input("monthly_debt_payment", monthly_debt_payment)
    trace.input("monthly_income",       monthly_income)
    trace.input("is_regulated",         is_regulated)
    trace.input("year",                 year)

    dti_raw   = payment / income
    dti       = round_apply(dti_raw, 4, RoundingPolicy.HALF_EVEN)
    within_cap = dti <= cap_rate

    trace.step("cap_rate",   str(cap_rate))
    trace.step("dti_raw",    str(dti_raw))
    trace.step("within_cap", str(within_cap))
    trace.output(str(dti))

    resp = {
        "dti":            str(dti),
        "within_cap":     within_cap,
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
