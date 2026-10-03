"""Korean severance (퇴직금) tax calculator.

Author: 최진호
Date: 2026-04-24
Modified: 2026-10-03

퇴직소득세 계산 (소득세법 제48조·제55조, 시행령 제105조):

  1. 퇴직급여 - 비과세 = 퇴직소득금액
  2. 근속연수공제 = min(근속연수 구간 공제액, 퇴직소득금액)  (제48조제2항)
     환산급여 = (퇴직소득금액 - 근속연수공제) * 12 / 근속연수
  3. 환산급여공제 테이블 적용 -> 과세표준(환산과세표준)
  4. 기본세율 적용 -> 환산산출세액
  5. 산출세액 = 환산산출세액 * 근속연수 / 12
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
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class KrSeverancePayResult(PolicyResult):
    severance:           str
    non_taxable:         str
    taxable_severance:   str
    service_years:       str
    service_deduction:   str
    converted_salary:    str
    converted_deduction: str
    converted_tax_base:  str
    converted_tax:       str
    tax:                 str


def _service_deduction(years: Decimal, brackets: list[dict[str, Any]]) -> Decimal:
    """근속연수공제 계산 (구간별 base + marginal * excess)."""
    for bracket in brackets:
        ylow  = Decimal(str(bracket["years_from"]))
        yhigh = bracket["years_to"]
        yhi_d: Decimal | None = None if yhigh is None else Decimal(str(yhigh))
        base  = Decimal(str(bracket["base"]))
        marg  = Decimal(str(bracket["marginal"]))

        if yhi_d is None or years <= yhi_d:
            excess = years - ylow
            return base + marg * excess
    return Decimal("0")


def _converted_salary_deduction(
    converted:  Decimal,
    brackets:   list[dict[str, Any]],
) -> Decimal:
    """환산급여공제 계산."""
    for bracket in brackets:
        low      = Decimal(str(bracket["lower"]))
        upper    = bracket["upper"]
        upper_d: Decimal | None = None if upper is None else Decimal(str(upper))
        base     = Decimal(str(bracket["base"]))
        marg     = Decimal(str(bracket["marginal"]))

        if upper_d is None or converted <= upper_d:
            excess = converted - low
            if excess < Decimal("0"):
                excess = Decimal("0")
            return base + marg * excess
    return Decimal("0")


@REGISTRY.tool(
    namespace="payroll",
    name="kr_severance_pay",
    description=(
        "퇴직소득세(소득세법 제48조·제55조)를 구한다. 퇴직급여총액, 근속연수(년, 소수 가능), 비과세액(원 문자열)에서 "
        "근속연수공제, 환산급여(12배 후 근속연수로 나눔)공제, 기본세율 누진을 적용하고 근속연수 비율로 환원해 원 단위 "
        "반올림한다. 1년 미만 끝수는 1년으로 올려 쓰며 지방소득세는 포함하지 않는다. 근속연수를 개월 수로 넣으면 안 된다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_severance_pay(
    severance_amount:    str,
    service_years:       str,
    year:                int,
    non_taxable:         str = "0",
) -> KrSeverancePayResult:
    """Calculate Korean severance tax (퇴직소득세).

    Args:
        severance_amount: 퇴직급여총액(원, 비과세 포함 총지급액)
        service_years:    근속연수(Decimal string, 연 단위. 소수 가능)
        year:             귀속연도
        non_taxable:      비과세 퇴직급여(원)

    Returns:
        {severance, non_taxable, taxable_severance, service_years,
         service_deduction, converted_salary, converted_deduction,
         converted_tax_base, converted_tax, tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_severance_pay",
        formula=(
            "근속연수공제 = min(구간 공제액, 퇴직소득금액); "
            "환산급여 = (퇴직소득금액 - 근속연수공제) * 12 / 근속연수; "
            "환산과세표준 = 환산급여 - 환산급여공제; "
            "환산산출세액 = progressive(환산과세표준); "
            "산출세액 = 환산산출세액 * 근속연수 / 12"
        ),
    )

    total   = D(severance_amount)
    nontax  = D(non_taxable)
    years   = D(service_years)

    if total < Decimal("0"):
        raise InvalidInputError("severance_amount는 0 이상이어야 합니다.")
    if nontax < Decimal("0"):
        raise InvalidInputError("non_taxable은 0 이상이어야 합니다.")
    if nontax > total:
        raise InvalidInputError("non_taxable은 severance_amount를 초과할 수 없습니다.")
    if years <= Decimal("0"):
        raise InvalidInputError("service_years는 0보다 커야 합니다.")

    policy_doc = policy_load("payroll", "kr_severance", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("severance_amount", severance_amount)
    trace.input("service_years",    service_years)
    trace.input("year",             year)
    trace.input("non_taxable",      non_taxable)
    trace.input("policy_version",   pv)

    taxable_severance = total - nontax

    # 근속연수의 1년 미만 기간은 1년으로 본다 (제48조제1항 각 호 외의 부분)
    service_years_ceil = years.to_integral_value(rounding="ROUND_CEILING")
    service_ded_table  = _service_deduction(service_years_ceil, data["service_deduction_brackets"])

    # 퇴직소득금액이 근속연수공제에 미달하면 퇴직소득금액을 공제액으로 한다 (제48조제2항)
    service_ded   = service_ded_table if service_ded_table <= taxable_severance else taxable_severance
    after_service = taxable_severance - service_ded

    # 환산급여
    converted = after_service * Decimal("12") / service_years_ceil

    # 환산급여공제
    conv_ded  = _converted_salary_deduction(
        converted, data["converted_salary_deduction_brackets"]
    )
    conv_base = converted - conv_ded
    if conv_base < Decimal("0"):
        conv_base = Decimal("0")

    conv_tax, _eff, _marg, breakdown = _calc_progressive(
        conv_base, data["tax_brackets"], RoundingPolicy.HALF_UP, 0
    )

    # 산출세액 = 환산세액 * 근속연수 / 12
    raw_tax = conv_tax * service_years_ceil / Decimal("12")
    tax     = round_apply(raw_tax, 0, RoundingPolicy.HALF_UP)

    trace.step("taxable_severance",    str(taxable_severance))
    trace.step("service_years_ceil",   str(service_years_ceil))
    trace.step("service_deduction_table", str(service_ded_table))
    trace.step("service_deduction",    str(service_ded))
    trace.step("converted_salary",     str(converted))
    trace.step("converted_deduction",  str(conv_ded))
    trace.step("converted_tax_base",   str(conv_base))
    trace.step("converted_tax",        str(conv_tax))
    trace.step("breakdown",            breakdown)
    trace.output(str(tax))

    resp: dict[str, Any] = {
        "severance":            str(total),
        "non_taxable":          str(nontax),
        "taxable_severance":    str(taxable_severance),
        "service_years":        str(service_years_ceil),
        "service_deduction":    str(service_ded),
        "converted_salary":     str(converted),
        "converted_deduction":  str(conv_ded),
        "converted_tax_base":   str(conv_base),
        "converted_tax":        str(conv_tax),
        "tax":                  str(tax),
        "policy_version":       pv,
        "trace":                trace.to_dict(),
    }
    return cast(KrSeverancePayResult, enrich_response(resp, policy_doc))
