"""Korean corporate income tax (법인세) calculator.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03

법인세법 제55조제1항 산출세액과 조세특례제한법 제132조제1항 최저한세:
  - 산출세액 = 과세표준에 제55조제1항제1호(일반) 또는 제2호(제60조의2제1항제1호 해당 법인) 세율
  - 최저한세액 = 최저한세 대상 손금산입·소득공제 전 과세표준 x 최저한세율
  - 감면 후 세액이 최저한세액에 미달하면 미달분만큼 감면을 배제한다. 감면이 없으면 산출세액 그대로다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.modules.tax.progressive import (
    BracketBreakdown,
    _calc_progressive,
    _parse_rounding,
)
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_GRADUATION_PERIODS = frozenset(["none", "first_3y", "next_2y"])


class TaxKrCorporateResult(PolicyResult):
    base_tax:               str
    minimum_tax:            str
    reductions:             str
    minimum_tax_adjustment: str
    tax:                    str
    effective_rate:         str
    marginal_rate:          str
    breakdown:              list[BracketBreakdown]


def _calc_minimum_tax(
    base:       Decimal,
    is_small:   bool,
    graduation: str,
    data:       dict[str, Any],
) -> Decimal:
    """Compute minimum tax amount (조특법 §132①).

    Small firm: flat `small` rate.
    Firm within the SME graduation grace period: flat `sme_graduation` rate.
    General firm: progressive brackets in `general_brackets`.
    """
    if is_small:
        return base * D(str(data["small"]))
    if graduation != "none":
        return base * D(str(data["sme_graduation"][graduation]))

    lower: Decimal = Decimal("0")
    total = Decimal("0")
    for bracket in data["general_brackets"]:
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))
        upper: Decimal | None = None if upper_raw is None else D(str(upper_raw))

        if upper is None:
            seg = base - lower if base > lower else Decimal("0")
            total += seg * rate
            break
        cap = min(base, upper)
        seg = cap - lower if cap > lower else Decimal("0")
        total += seg * rate
        lower = upper
        if base <= upper:
            break
    return total


@REGISTRY.tool(
    namespace="tax",
    name="kr_corporate",
    description=(
        "한국 법인세를 계산한다(법인세법 제55조, 조세특례제한법 제132조). taxable_income 은 과세표준(원, Decimal 문자열)이고 "
        "누진 구간 산출세액(base_tax)에서 reductions 를 빼되 최저한세에 미달하는 감면은 배제해 tax 를 정한다. "
        "is_small_rental_corp 는 제55조제1항제2호 세율, is_small 과 sme_graduation_period 는 최저한세율을 바꾼다. "
        "감면 전 과세표준이 다르면 pre_deduction_income 을 따로 넣어야 최저한세가 맞는다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_corporate(
    taxable_income:        str,
    year:                  int,
    is_small:              bool       = False,
    rounding:              str        = "HALF_UP",
    decimals:              int        = 0,
    is_small_rental_corp:  bool       = False,
    sme_graduation_period: str        = "none",
    reductions:            str        = "0",
    pre_deduction_income:  str | None = None,
) -> TaxKrCorporateResult:
    """Calculate Korean corporate income tax with the minimum-tax rule.

    Args:
        taxable_income:        과세표준 (Decimal string, 원)
        year:                  사업연도 개시일이 속하는 연도
        is_small:              중소기업 여부 (최저한세 7%)
        rounding:              반올림 정책
        decimals:              소수점 자리수
        is_small_rental_corp:  법인세법 제60조의2제1항제1호 해당 법인 여부 (제55조제1항제2호 세율)
        sme_graduation_period: 최초로 중소기업에 해당하지 않게 된 과세연도 기준 유예 구간.
                               none | first_3y (개시일부터 3년 이내, 8%) | next_2y (그다음 2년 이내, 9%)
        reductions:            최저한세 적용 대상 세액공제·감면 합계 (조특법 제132조제1항제3호·제4호, 원)
        pre_deduction_income:  최저한세 대상 손금산입·소득공제(제132조제1항제2호) 전 과세표준 (원).
                               생략하면 taxable_income 과 같다.

    Returns:
        {base_tax, minimum_tax, reductions, minimum_tax_adjustment, tax,
         effective_rate, marginal_rate, breakdown, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_corporate",
        formula=(
            "base_tax = 누진세율 적용(taxable_income); "
            "minimum_tax = 감면 전 과세표준 x 최저한세율; "
            "after_relief = max(0, base_tax - reductions); "
            "tax = max(after_relief, min(minimum_tax, 누진세율 적용(감면 전 과세표준)))"
        ),
    )

    if sme_graduation_period not in _GRADUATION_PERIODS:
        raise InvalidInputError(
            f"sme_graduation_period는 {sorted(_GRADUATION_PERIODS)} 중 하나여야 합니다."
        )
    if is_small and sme_graduation_period != "none":
        raise InvalidInputError(
            "sme_graduation_period는 중소기업에 해당하지 않게 된 법인용이므로 is_small=True 와 함께 쓸 수 없습니다."
        )

    policy_enum = _parse_rounding(rounding)
    income      = D(taxable_income)
    relief      = D(reductions)

    if income < Decimal("0"):
        raise InvalidInputError("taxable_income는 0 이상이어야 합니다.")
    if relief < Decimal("0"):
        raise InvalidInputError("reductions는 0 이상이어야 합니다.")

    min_base = income if pre_deduction_income is None else D(pre_deduction_income)
    if min_base < income:
        raise InvalidInputError("pre_deduction_income은 taxable_income 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_corporate", year)
    data       = policy_doc["data"]
    brackets   = data["small_rental_brackets"] if is_small_rental_corp else data["brackets"]
    pv         = policy_doc["policy_version"]

    trace.input("taxable_income",        taxable_income)
    trace.input("year",                  year)
    trace.input("is_small",              is_small)
    trace.input("rounding",              rounding)
    trace.input("is_small_rental_corp",  is_small_rental_corp)
    trace.input("sme_graduation_period", sme_graduation_period)
    trace.input("reductions",            reductions)
    trace.input("pre_deduction_income",  pre_deduction_income)
    trace.input("policy_version",        pv)

    base_tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        income, brackets, policy_enum, decimals
    )

    min_tax_raw = _calc_minimum_tax(min_base, is_small, sme_graduation_period, data["minimum_tax"])
    min_tax     = min_tax_raw.quantize(Decimal("1")) if decimals == 0 else min_tax_raw

    if min_base == income:
        tax_without_relief = base_tax
    else:
        tax_without_relief, _, _, _ = _calc_progressive(min_base, brackets, policy_enum, decimals)
    floor_tax = min_tax if min_tax < tax_without_relief else tax_without_relief

    after_relief = base_tax - relief if base_tax > relief else Decimal("0")
    tax_final    = after_relief if after_relief >= floor_tax else floor_tax
    adjustment   = tax_final - after_relief

    trace.step("base_tax",               str(base_tax))
    trace.step("minimum_tax_base",       str(min_base))
    trace.step("minimum_tax",            str(min_tax))
    trace.step("after_relief",           str(after_relief))
    trace.step("minimum_tax_adjustment", str(adjustment))
    trace.step("breakdown",              breakdown)
    trace.output(str(tax_final))

    resp: dict[str, Any] = {
        "base_tax":               str(base_tax),
        "minimum_tax":            str(min_tax),
        "reductions":             str(relief),
        "minimum_tax_adjustment": str(adjustment),
        "tax":                    str(tax_final),
        "effective_rate":         str(eff_rate),
        "marginal_rate":          str(marginal_rate),
        "breakdown":              breakdown,
        "policy_version":         pv,
        "trace":                  trace.to_dict(),
    }
    return cast(TaxKrCorporateResult, enrich_response(resp, policy_doc))
