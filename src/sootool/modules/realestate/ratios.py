"""DSR, LTV, DTI ratio calculators for Korean real estate.

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

Policy reference: kr_dsr_ltv_{year}.yaml
- DSR cap: 은행권 40%, 2금융권 50%, 스트레스 금리 하한 안내
- LTV: 규제지역 여부, 수도권 여부, 주택 수, 생애최초 여부에 따른 비율과
  수도권·규제지역 주택가격별 주담대 금액 한도
- DTI: 규제지역 40%, 규제지역 외 수도권(아파트) 60%, 수도권 외 비규제지역 한도 없음
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
from sootool.modules.realestate._kr_local_tax import lookup_upper_table
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_MORTGAGE_REGIONS: set[str] = {"capital_or_regulated", "non_capital"}


class RealestateKrDsrResult(PolicyResult):
    dsr:               str
    within_cap:        bool
    cap:               str
    stress_rate_floor: str | None


class RealestateKrLtvResult(PolicyResult):
    ltv:        str
    within_cap: bool
    cap_rate:   str
    amount_cap: str | None
    max_loan:   str


class RealestateKrDtiResult(PolicyResult):
    dti:        str
    within_cap: bool
    cap:        str | None


def _stress_rate_floor(data: dict[str, Any], mortgage_region: str | None) -> Decimal | None:
    """주담대 지역 구분에 따른 스트레스 금리 하한. 지역이 없거나 정책에 값이 없으면 None."""
    stress = data.get("stress_dsr")
    if mortgage_region is None or not stress:
        return None
    key = (
        "capital_or_regulated_mortgage_floor" if mortgage_region == "capital_or_regulated"
        else "non_capital_mortgage_floor"
    )
    raw = stress.get(key)
    return D(str(raw)) if raw is not None else None


@REGISTRY.tool(
    namespace="realestate",
    name="kr_dsr",
    description=(
        "DSR(총부채원리금상환비율 = 연간 원리금 상환액 / 연간 소득, 원 단위 문자열)을 계산하고 한도 이내인지 "
        "판정한다. 소수 4자리 HALF_EVEN 반올림, 한도는 은행권 40%, 2금융권(is_nonbank) 50%. "
        "mortgage_region 을 주면 스트레스 금리 하한을 반환하지만 상환액에 가산해 주지는 않는다. "
        "오용 예: 월 상환액과 연 소득을 섞어 입력."
    ),
    version="1.1.0",
    policy=True,
)
def realestate_kr_dsr(
    annual_debt_payment: str,
    annual_income:       str,
    year:                int,
    is_nonbank:          bool       = False,
    mortgage_region:     str | None = None,
) -> RealestateKrDsrResult:
    """Calculate DSR ratio.

    Args:
        annual_debt_payment: 연간 원리금 상환 총액 (원, Decimal string). 스트레스 DSR 기준으로
                             판정하려면 대출금리에 stress_rate_floor 를 더해 산정한 상환액을 넣는다
        annual_income:       연간 소득 (원, Decimal string)
        year:                적용 기준 연도
        is_nonbank:          2금융권 대출 여부 (한도 50%)
        mortgage_region:     주담대 지역 구분 "capital_or_regulated"(수도권·규제지역) 또는
                             "non_capital"(그 외). 주면 스트레스 금리 하한을 반환

    Returns:
        {dsr: str, within_cap: bool, cap: str, stress_rate_floor: str | None, policy_version, trace}
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
    if mortgage_region is not None and mortgage_region not in _MORTGAGE_REGIONS:
        raise InvalidInputError(f"mortgage_region은 {sorted(_MORTGAGE_REGIONS)} 중 하나여야 합니다.")

    policy_doc = policy_load("realestate", "kr_dsr_ltv", year)
    data = policy_doc["data"]
    pv   = policy_doc["policy_version"]

    if is_nonbank and data.get("dsr_cap_nonbank") is not None:
        cap_rate = D(str(data["dsr_cap_nonbank"]))
    else:
        cap_rate = D(str(data["dsr_cap"]))
    stress_floor = _stress_rate_floor(data, mortgage_region)

    trace.input("annual_debt_payment", annual_debt_payment)
    trace.input("annual_income",       annual_income)
    trace.input("year",                year)
    trace.input("is_nonbank",          is_nonbank)
    trace.input("mortgage_region",     mortgage_region)

    dsr_raw   = debt / income
    dsr       = round_apply(dsr_raw, 4, RoundingPolicy.HALF_EVEN)
    within_cap = dsr <= cap_rate

    trace.step("dsr_raw",           str(dsr_raw))
    trace.step("cap",               str(cap_rate))
    trace.step("stress_rate_floor", str(stress_floor) if stress_floor is not None else None)
    trace.step("within_cap",        str(within_cap))
    trace.output(str(dsr))

    resp: dict[str, Any] = {
        "dsr":               str(dsr),
        "within_cap":        within_cap,
        "cap":               str(cap_rate),
        "stress_rate_floor": str(stress_floor) if stress_floor is not None else None,
        "policy_version":    pv,
        "trace":             trace.to_dict(),
    }
    return cast(RealestateKrDsrResult, enrich_response(resp, policy_doc))


def _ltv_cap_rate(
    ltv_data:            dict[str, Any],
    is_regulated:        bool,
    is_capital_area:     bool,
    house_count:         int,
    is_first_time_buyer: bool,
) -> Decimal:
    tight = is_regulated or is_capital_area
    if house_count >= 2:
        if is_regulated:
            return D(str(ltv_data["regulated_multi_house"]))
        if is_capital_area and ltv_data.get("capital_non_regulated_multi_house") is not None:
            return D(str(ltv_data["capital_non_regulated_multi_house"]))
        return D(str(ltv_data["non_regulated_multi_house"]))
    if is_first_time_buyer:
        key = "first_time_buyer_capital_or_regulated" if tight else "first_time_buyer_other"
        if ltv_data.get(key) is not None:
            return D(str(ltv_data[key]))
    if is_regulated:
        return D(str(ltv_data["regulated_first_house"]))
    return D(str(ltv_data["non_regulated_first_house"]))


@REGISTRY.tool(
    namespace="realestate",
    name="kr_ltv",
    description=(
        "LTV(대출액 / 주택가액, 원 단위 문자열, 소수 4자리 HALF_EVEN)를 계산하고 한도 이내 여부와 최대 "
        "대출액을 구한다. 한도 비율은 규제지역·수도권, 주택 수, 생애최초 여부로 정해지며 규제지역·수도권 "
        "다주택은 추가 구입 0%다. 수도권·규제지역은 시가 15억 이하 6억, 25억 이하 4억, 초과 2억 금액 한도도 "
        "적용. 오용 예: house_count 에 대출 전 주택 수 입력."
    ),
    version="1.1.0",
    policy=True,
)
def realestate_kr_ltv(
    loan_amount:         str,
    property_value:      str,
    year:                int,
    is_regulated:        bool,
    house_count:         int,
    is_capital_area:     bool = False,
    is_first_time_buyer: bool = False,
) -> RealestateKrLtvResult:
    """Calculate LTV ratio and check against policy cap.

    Args:
        loan_amount:         대출액 (원, Decimal string)
        property_value:      주택가액(시가) (원, Decimal string)
        year:                적용 기준 연도
        is_regulated:        규제지역(투기과열지구·조정대상지역) 여부
        house_count:         보유 주택 수 (대출 후 기준)
        is_capital_area:     수도권(서울·경기·인천) 여부
        is_first_time_buyer: 생애최초 주택구입 여부 (house_count == 1 일 때 적용)

    Returns:
        {ltv: str, within_cap: bool, cap_rate: str, amount_cap: str | None, max_loan: str,
         policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_ltv",
        formula=(
            "LTV = loan_amount / property_value; "
            "max_loan = min(property_value * ltv_cap, 주택가격별 한도, 생애최초 한도)"
        ),
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

    first_time = is_first_time_buyer and house_count == 1
    cap_rate   = _ltv_cap_rate(ltv_data, is_regulated, is_capital_area, house_count, first_time)

    amount_caps: list[Decimal] = []
    price_table = data.get("mortgage_amount_cap_capital_or_regulated")
    if (is_regulated or is_capital_area) and price_table:
        amount_caps.append(lookup_upper_table(value, price_table, "cap"))
    if first_time and ltv_data.get("first_time_buyer_loan_cap") is not None:
        amount_caps.append(D(str(ltv_data["first_time_buyer_loan_cap"])))
    amount_cap = min(amount_caps) if amount_caps else None

    trace.input("loan_amount",         loan_amount)
    trace.input("property_value",      property_value)
    trace.input("is_regulated",        is_regulated)
    trace.input("house_count",         house_count)
    trace.input("is_capital_area",     is_capital_area)
    trace.input("is_first_time_buyer", is_first_time_buyer)
    trace.input("year",                year)

    ratio_loan = round_apply(value * cap_rate, 0, RoundingPolicy.FLOOR)
    max_loan   = min(ratio_loan, amount_cap) if amount_cap is not None else ratio_loan
    ltv_raw    = loan / value
    ltv        = round_apply(ltv_raw, 4, RoundingPolicy.HALF_EVEN)
    # 반올림 전 비율로 판정해 한도 초과(예: cap=0, loan>0)를 놓치지 않는다
    within_cap = ltv_raw <= cap_rate and (amount_cap is None or loan <= amount_cap)

    trace.step("cap_rate",   str(cap_rate))
    trace.step("amount_cap", str(amount_cap) if amount_cap is not None else None)
    trace.step("max_loan",   str(max_loan))
    trace.step("ltv_raw",    str(ltv_raw))
    trace.step("within_cap", str(within_cap))
    trace.output(str(ltv))

    resp: dict[str, Any] = {
        "ltv":            str(ltv),
        "within_cap":     within_cap,
        "cap_rate":       str(cap_rate),
        "amount_cap":     str(amount_cap) if amount_cap is not None else None,
        "max_loan":       str(max_loan),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return cast(RealestateKrLtvResult, enrich_response(resp, policy_doc))


@REGISTRY.tool(
    namespace="realestate",
    name="kr_dti",
    description=(
        "DTI(총부채상환비율 = 월 원리금 상환액 / 월 소득, 원 단위 문자열)를 계산하고 한도 이내인지 판정한다. "
        "소수 4자리 HALF_EVEN 반올림, 규제지역 40%, 규제지역 외 수도권(아파트 담보) 60%, 수도권 외 "
        "비규제지역은 한도 없음(cap 이 null, within_cap 은 true). 오용 예: 연간 금액을 월 금액 자리에 입력."
    ),
    version="1.1.0",
    policy=True,
)
def realestate_kr_dti(
    monthly_debt_payment: str,
    monthly_income:       str,
    year:                 int,
    is_regulated:         bool,
    is_capital_area:      bool = False,
) -> RealestateKrDtiResult:
    """Calculate DTI ratio.

    Args:
        monthly_debt_payment: 월 원리금 상환액 (원, Decimal string)
        monthly_income:       월 소득 (원, Decimal string)
        year:                 적용 기준 연도
        is_regulated:         규제지역(투기지역·투기과열지구) 여부
        is_capital_area:      수도권 여부. 비규제지역에서는 수도권일 때만 한도를 적용

    Returns:
        {dti: str, within_cap: bool, cap: str | None, policy_version, trace}
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

    if is_regulated:
        raw_cap = dti_data["regulated"]
    elif is_capital_area or "non_capital" not in dti_data:
        raw_cap = dti_data["non_regulated"]
    else:
        raw_cap = dti_data["non_capital"]
    cap_rate = D(str(raw_cap)) if raw_cap is not None else None

    trace.input("monthly_debt_payment", monthly_debt_payment)
    trace.input("monthly_income",       monthly_income)
    trace.input("is_regulated",         is_regulated)
    trace.input("is_capital_area",      is_capital_area)
    trace.input("year",                 year)

    dti_raw   = payment / income
    dti       = round_apply(dti_raw, 4, RoundingPolicy.HALF_EVEN)
    within_cap = cap_rate is None or dti <= cap_rate

    trace.step("cap_rate",   str(cap_rate) if cap_rate is not None else None)
    trace.step("dti_raw",    str(dti_raw))
    trace.step("within_cap", str(within_cap))
    trace.output(str(dti))

    resp: dict[str, Any] = {
        "dti":            str(dti),
        "within_cap":     within_cap,
        "cap":            str(cap_rate) if cap_rate is not None else None,
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return cast(RealestateKrDtiResult, enrich_response(resp, policy_doc))
