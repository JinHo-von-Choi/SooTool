"""US capital gains tax calculator (tax_us.capital_gains).

Long-term capital gains: 0%/15%/20% three brackets (per filing status), measured on
total taxable income with the gain stacked on top of ordinary taxable income
(IRC 1(h)(1); Form 1040 Qualified Dividends and Capital Gain Tax Worksheet).
Short-term: ordinary income rates on the slice the gain adds above ordinary income.
Net Investment Income Tax (NIIT): 3.8% optional on MAGI over threshold.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult, PolicyVersion
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax.progressive import BracketBreakdown, _parse_rounding
from sootool.modules.tax_us._brackets import slice_tax
from sootool.modules.tax_us.federal_income import _validate_filing_status
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class TaxUsCapitalGainsResult(PolicyResult):
    tax:                     str
    ltcg_tax:                str
    niit:                    str
    niit_base:               str
    marginal_rate:           str
    breakdown:               list[BracketBreakdown]
    term:                    str
    method:                  str
    ordinary_taxable_income: str
    taxable_income:          str
    filing_status:           str
    ordinary_policy_version: PolicyVersion


@REGISTRY.tool(
    namespace="tax_us",
    name="capital_gains",
    description=(
        "미국 연방 자본이득세를 계산한다. 장기(long)는 0%/15%/20% 구간을 신고 유형별로 적용하며 ordinary_taxable_income 위에 양도소득을 쌓아 과세하고, "
        "단기(short)는 그 증가분에 일반 소득세율을 쓴다. apply_niit=true 이면 순투자소득세 3.8%를 더한다. "
        "금액은 USD Decimal 문자열이고 기본은 소수 둘째 자리 HALF_UP이다. "
        "ordinary_taxable_income 을 생략하면 0으로 보므로 다른 소득이 있으면 반드시 넣어야 한다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_us_capital_gains(
    gain:                     str,
    filing_status:            str,
    year:                     int,
    term:                     str  = "long",
    magi:                     str  | None = None,
    apply_niit:               bool = False,
    ordinary_taxable_income:  str  | None = None,
    rounding:                 str  = "HALF_UP",
    decimals:                 int  = 2,
) -> TaxUsCapitalGainsResult:
    """Calculate US capital gains tax.

    Args:
        gain:                    capital gain (USD, Decimal string, 0 이상)
        filing_status:           single/married_joint/married_separate/head_of_household
                                 (qualifying_surviving_spouse 는 married_joint 표 적용)
        year:                    tax year (2025, 2026)
        term:                    "long" (LTCG 0/15/20) 또는 "short" (ordinary)
        magi:                    Modified Adjusted Gross Income (NIIT 임계치 평가용).
                                 None이면 ordinary_taxable_income + gain 을 쓴다
                                 (MAGI 는 과세표준 이상이므로 하한값).
        apply_niit:              True면 NIIT 3.8% 추가 계산
        ordinary_taxable_income: 양도소득을 뺀 과세표준(USD, 1040 QDCG 워크시트 line 5).
                                 양도소득은 이 금액 위에 쌓인다. None이면 0.
        rounding:                반올림 정책 (기본 HALF_UP)
        decimals:                소수점 자리수 (기본 2, USD cents)

    Returns:
        {tax, ltcg_tax, niit, niit_base, marginal_rate, breakdown, term, method,
         ordinary_taxable_income, taxable_income, filing_status, policy_version,
         ordinary_policy_version, trace}
        ltcg_tax 는 양도소득에 귀속되는 세액(일반소득 세액 제외)이다.
    """
    trace = CalcTrace(
        tool="tax_us.capital_gains",
        formula=(
            "TI = ordinary + gain; "
            "LTCG: gain_tax = min(sum over LTCG brackets of rate * overlap((ordinary, TI], bracket), "
            "tax_ordinary(TI) - tax_ordinary(ordinary)); "
            "Short-term: gain_tax = tax_ordinary(TI) - tax_ordinary(ordinary); "
            "NIIT: tax += 0.038 * min(gain, max(MAGI - threshold, 0))"
        ),
    )

    schedule = _validate_filing_status(filing_status)
    if term not in {"long", "short"}:
        raise InvalidInputError(
            f"term은 'long' 또는 'short'여야 합니다. 입력: '{term}'"
        )

    policy = _parse_rounding(rounding)
    gain_d = D(gain)

    if gain_d < Decimal("0"):
        raise InvalidInputError("gain은 0 이상이어야 합니다.")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")

    ordinary_d = Decimal("0") if ordinary_taxable_income is None else D(ordinary_taxable_income)
    if ordinary_d < Decimal("0"):
        raise InvalidInputError("ordinary_taxable_income은 0 이상이어야 합니다.")
    total_ti = ordinary_d + gain_d

    # 일반소득 세율표를 먼저 읽고 양도소득 정책을 나중에 읽어 무결성 메타가 주 정책을 가리키게 한다.
    fed_policy_doc = policy_load("tax_us", "federal_income", year)
    fed_brackets   = fed_policy_doc["data"]["brackets"][schedule]
    policy_doc     = policy_load("tax_us", "capital_gains", year)
    data           = policy_doc["data"]
    pv             = policy_doc["policy_version"]

    trace.input("gain",                    gain)
    trace.input("filing_status",           filing_status)
    trace.input("year",                    year)
    trace.input("term",                    term)
    trace.input("magi",                    magi)
    trace.input("apply_niit",              apply_niit)
    trace.input("ordinary_taxable_income", ordinary_taxable_income)
    trace.input("policy_version",          pv)
    trace.step("filing_status_schedule",   schedule)
    trace.step("taxable_income",           str(total_ti))

    ord_raw, ord_marginal, ord_breakdown = slice_tax(ordinary_d, total_ti, fed_brackets)

    if term == "long":
        ltcg_raw, ltcg_marginal, ltcg_breakdown = slice_tax(
            ordinary_d, total_ti, data["ltcg_brackets"][schedule]
        )
        trace.step("ltcg_rate_tax",    str(ltcg_raw))
        trace.step("regular_rate_tax", str(ord_raw))
        if ord_raw < ltcg_raw:
            gain_raw, primary_rate, breakdown, method = (
                ord_raw, ord_marginal, ord_breakdown, "regular_tax"
            )
        else:
            gain_raw, primary_rate, breakdown, method = (
                ltcg_raw, ltcg_marginal, ltcg_breakdown, "qdcg_worksheet"
            )
    else:
        gain_raw, primary_rate, breakdown, method = (
            ord_raw, ord_marginal, ord_breakdown, "ordinary_rates"
        )

    ltcg_tax  = round_apply(gain_raw, decimals, policy)
    tax_total = ltcg_tax
    trace.step("method", method)

    # NIIT calculation (optional)
    niit_amount = Decimal("0")
    niit_base   = Decimal("0")
    if apply_niit:
        niit_cfg    = data["niit"]
        niit_rate   = D(str(niit_cfg["rate"]))
        threshold   = D(str(niit_cfg["thresholds"][schedule]))

        if magi is None:
            magi_d = total_ti
        else:
            magi_d = D(magi)
            if magi_d < Decimal("0"):
                raise InvalidInputError("magi는 0 이상이어야 합니다.")

        excess      = magi_d - threshold
        if excess < Decimal("0"):
            excess = Decimal("0")
        niit_base   = gain_d if gain_d < excess else excess
        niit_raw    = niit_base * niit_rate
        niit_amount = round_apply(niit_raw, decimals, policy)
        tax_total   = tax_total + niit_amount

        trace.step("niit_magi",        str(magi_d))
        trace.step("niit_threshold",   str(threshold))
        trace.step("niit_excess_magi", str(excess))
        trace.step("niit_base",        str(niit_base))
        trace.step("niit_rate",        str(niit_rate))

    trace.step("breakdown", breakdown)
    trace.output(str(tax_total))

    resp: dict[str, Any] = {
        "tax":                     str(tax_total),
        "ltcg_tax":                str(ltcg_tax),
        "niit":                    str(niit_amount),
        "niit_base":               str(niit_base),
        "marginal_rate":           str(primary_rate),
        "breakdown":               breakdown,
        "term":                    term,
        "method":                  method,
        "ordinary_taxable_income": str(ordinary_d),
        "taxable_income":          str(total_ti),
        "filing_status":           filing_status,
        "policy_version":          pv,
        "ordinary_policy_version": fed_policy_doc["policy_version"],
        "trace":                   trace.to_dict(),
    }
    return cast(TaxUsCapitalGainsResult, enrich_response(resp, policy_doc))
