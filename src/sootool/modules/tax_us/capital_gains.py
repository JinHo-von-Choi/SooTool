"""US capital gains tax calculator (tax_us.capital_gains).

Long-term capital gains: 0%/15%/20% three brackets (per filing status).
Short-term: delegates to tax_us.federal_income (ordinary income rate).
Net Investment Income Tax (NIIT): 3.8% optional on MAGI over threshold.

Author: 최진호
Date: 2026-04-23
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
from sootool.modules.tax.progressive import (
    _calc_progressive,
    _parse_rounding,
)
from sootool.modules.tax_us.federal_income import _validate_filing_status
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


def _calc_ltcg(
    gain:        Decimal,
    brackets:    list[dict[str, Any]],
    rounding:    RoundingPolicy,
    decimals:    int,
) -> tuple[Decimal, Decimal, list[dict[str, Any]]]:
    """Calculate LTCG tax using 3-bracket rate schedule (0%/15%/20%).

    Returns (tax, marginal_rate, breakdown).
    """
    tax, _eff_rate, marginal, breakdown = _calc_progressive(
        gain, brackets, rounding, decimals
    )
    return tax, marginal, breakdown


@REGISTRY.tool(
    namespace="tax_us",
    name="capital_gains",
    description=(
        "미국 자본이득세 계산. Long-term (0%/15%/20%, filing status별 구간) 또는 "
        "Short-term (연방 소득세율 위임). Net Investment Income Tax (NIIT) 3.8% 옵션."
    ),
    version="1.0.0",
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
) -> dict[str, Any]:
    """Calculate US capital gains tax.

    Args:
        gain:                    capital gain (USD, Decimal string, 0 이상)
        filing_status:           single/married_joint/married_separate/head_of_household
        year:                    tax year (2025)
        term:                    "long" (LTCG 0/15/20) 또는 "short" (ordinary)
        magi:                    Modified Adjusted Gross Income (NIIT 임계치 평가용).
                                 None이면 gain만 사용.
        apply_niit:              True면 NIIT 3.8% 추가 계산
        ordinary_taxable_income: term="short"일 때 과세표준(USD). 미지정 시 gain 사용.
        rounding:                반올림 정책 (기본 HALF_UP)
        decimals:                소수점 자리수 (기본 2, USD cents)

    Returns:
        {tax, ltcg_tax, niit, niit_base, marginal_rate, breakdown, term,
         filing_status, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax_us.capital_gains",
        formula=(
            "LTCG: tax = sum((min(gain,upper)-lower)*rate for 3 brackets); "
            "NIIT: tax += 0.038 * min(gain, max(MAGI - threshold, 0)); "
            "Short-term: delegate to tax_us.federal_income"
        ),
    )

    _validate_filing_status(filing_status)
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

    policy_doc = policy_load("tax_us", "capital_gains", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("gain",           gain)
    trace.input("filing_status",  filing_status)
    trace.input("year",           year)
    trace.input("term",           term)
    trace.input("magi",           magi)
    trace.input("apply_niit",     apply_niit)
    trace.input("policy_version", pv)

    if term == "long":
        brackets = data["ltcg_brackets"][filing_status]
        ltcg_tax, marginal, breakdown = _calc_ltcg(gain_d, brackets, policy, decimals)
        tax_total    = ltcg_tax
        primary_rate = marginal
    else:
        # Short-term: delegate to federal_income via its _calc_progressive path.
        # Use ordinary_taxable_income if provided, otherwise the gain itself.
        ord_income_raw = ordinary_taxable_income if ordinary_taxable_income is not None else gain
        ord_income     = D(ord_income_raw)
        if ord_income < Decimal("0"):
            raise InvalidInputError("ordinary_taxable_income은 0 이상이어야 합니다.")

        fed_policy_doc = policy_load("tax_us", "federal_income", year)
        fed_brackets   = fed_policy_doc["data"]["brackets"][filing_status]
        ltcg_tax, _eff, marginal, breakdown = _calc_progressive(
            ord_income, fed_brackets, policy, decimals
        )
        tax_total    = ltcg_tax
        primary_rate = marginal

    # NIIT calculation (optional)
    niit_amount = Decimal("0")
    niit_base   = Decimal("0")
    if apply_niit:
        niit_cfg    = data["niit"]
        niit_rate   = D(str(niit_cfg["rate"]))
        threshold   = D(str(niit_cfg["thresholds"][filing_status]))

        if magi is None:
            # No MAGI given: assume MAGI == gain (conservative self-contained calc)
            magi_d = gain_d
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

        trace.step("niit_threshold",   str(threshold))
        trace.step("niit_excess_magi", str(excess))
        trace.step("niit_base",        str(niit_base))
        trace.step("niit_rate",        str(niit_rate))

    trace.step("breakdown", breakdown)
    trace.output(str(tax_total))

    resp = {
        "tax":              str(tax_total),
        "ltcg_tax":         str(ltcg_tax),
        "niit":             str(niit_amount),
        "niit_base":        str(niit_base),
        "marginal_rate":    str(primary_rate),
        "breakdown":        breakdown,
        "term":             term,
        "filing_status":    filing_status,
        "policy_version":   pv,
        "trace":            trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
