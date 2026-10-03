"""Korean inheritance tax (상속세) calculator.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03

상속세 및 증여세법 계산 순서:
  1. 기초·인적공제(제18조·제20조)와 일괄공제(제21조) 중 큰 금액. 배우자 단독상속이면 일괄공제 불가
  2. 배우자공제(제19조): 실제 상속액을 min(법정상속분 한도금액, 30억)으로 제한, 최소 5억
  3. 공제 종합한도(제24조): 과세가액 - 상속인 아닌 자 유증등 - 상속포기분 - 가산 사전증여재산
  4. 상속세산출세액(제26조), 신고세액공제(제69조제1항) 3%
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax.progressive import (
    BracketBreakdown,
    _calc_progressive,
    _parse_rounding,
)
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class InheritanceDeductions(TypedDict):
    """상속공제 구성. 모두 원 단위 Decimal 문자열이다."""

    general:   str
    personal:  str
    spouse:    str
    requested: str
    limit:     str
    total:     str


class TaxKrInheritanceResult(PolicyResult):
    gross_estate:            str
    deductions:              InheritanceDeductions
    taxable_base:            str
    computed_tax:            str
    generation_skip_surcharge: str
    tax:                     str
    filing_credit:           str
    tax_after_filing_credit: str
    effective_rate:          str
    marginal_rate:           str
    breakdown:               list[BracketBreakdown]


def _non_negative(name: str, value: str) -> Decimal:
    """금액 입력을 Decimal 로 바꾸고 음수를 거부한다."""
    amount = D(value)
    if amount < Decimal("0"):
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


def _resolve_spouse_deduction(
    has_spouse:         bool,
    spouse_inheritance: Decimal,
    legal_share_cap:    Decimal | None,
    deductions:         dict[str, Any],
) -> Decimal:
    """배우자 상속공제 (상속세 및 증여세법 제19조).

    제19조제1항: 실제 상속액을 min(법정상속분 한도금액, 30억) 한도로 공제한다.
    제19조제4항: 실제 상속액이 없거나 5억 미만이면 5억을 공제한다.
    배우자가 없으면 0 이다.
    """
    if not has_spouse:
        return Decimal("0")
    min_d = D(str(deductions["spouse_min"]))
    cap   = D(str(deductions["spouse_max"]))
    if legal_share_cap is not None and legal_share_cap < cap:
        cap = legal_share_cap
    allowed = spouse_inheritance if spouse_inheritance < cap else cap
    return allowed if allowed > min_d else min_d


def _personal_deduction(
    personal:                  dict[str, Any],
    children_count:            int,
    minor_years_total:         int,
    elderly_count:             int,
    disabled_life_years_total: int,
) -> Decimal:
    """그 밖의 인적공제 합계 (상속세 및 증여세법 제20조제1항)."""
    return (
        D(str(personal["child_each"]))             * children_count
        + D(str(personal["minor_per_year"]))       * minor_years_total
        + D(str(personal["elderly_each"]))         * elderly_count
        + D(str(personal["disabled_per_life_year"])) * disabled_life_years_total
    )


@REGISTRY.tool(
    namespace="tax",
    name="kr_inheritance",
    description=(
        "한국 상속세를 계산한다(상속세및증여세법 제18조~제21조·제24조·제26조·제69조). 금액은 원 단위 Decimal 문자열이다. "
        "기초·인적공제와 일괄공제 5억 중 큰 금액, 배우자공제(법정상속분 한도와 30억 중 작은 값, 최소 5억), 공제 종합한도를 적용한 뒤 "
        "10~50% 누진세율로 산출하고 세대생략 할증(제27조, 산출세액 x 받은 재산 비율 x 30%, 미성년 20억 초과 40%)을 더한 뒤 신고세액공제 3%를 "
        "따로 보여 준다. gross_estate 는 사전증여 가산 후 과세가액이며 할증 비율의 분모다. 배우자가 있으나 상속받지 않았으면 has_spouse=true 를 지정한다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_inheritance(
    gross_estate:              str,
    spouse_inheritance:        str,
    year:                      int,
    use_lump_sum:              bool        = True,
    rounding:                  str         = "HALF_UP",
    decimals:                  int         = 0,
    has_spouse:                bool | None = None,
    spouse_legal_share_cap:    str | None  = None,
    spouse_sole_heir:          bool        = False,
    children_count:            int         = 0,
    minor_years_total:         int         = 0,
    elderly_count:             int         = 0,
    disabled_life_years_total: int         = 0,
    bequest_to_non_heirs:      str         = "0",
    renounced_inheritance:     str         = "0",
    pre_gift_added:            str         = "0",
    timely_filing:             bool        = True,
    skipped_generation_amount: str         = "0",
    skipped_generation_minor:  bool        = False,
) -> TaxKrInheritanceResult:
    """Calculate Korean inheritance tax.

    Args:
        gross_estate:              상속세 과세가액 (제13조, 사전증여재산 가산 후, 원)
        spouse_inheritance:        배우자가 실제로 상속받은 금액 (원)
        year:                      과세연도
        use_lump_sum:              True 면 max(일괄공제 5억, 기초 2억 + 인적공제). False 면 기초 + 인적공제.
        rounding:                  반올림 정책
        decimals:                  소수점 자리수
        has_spouse:                배우자 생존 여부. 생략하면 spouse_inheritance > 0 으로 판단한다.
                                   배우자가 있으나 상속받지 않았으면 True 로 지정해야 5억이 공제된다.
        spouse_legal_share_cap:    제19조제1항제1호 한도금액 (A - B + C) x 법정상속분 - E (원).
                                   생략하면 30억 한도만 적용한다.
        spouse_sole_heir:          배우자 단독상속 여부 (제21조제2항, 일괄공제 배제)
        children_count:            자녀(태아 포함) 수 (제20조제1항제1호)
        minor_years_total:         미성년 상속인·동거가족별 19세까지 연수의 합 (1년 미만은 1년)
        elderly_count:             배우자를 제외한 65세 이상 상속인·동거가족 수
        disabled_life_years_total: 장애인별 기대여명 연수의 합 (1년 미만은 1년)
        bequest_to_non_heirs:      선순위 상속인이 아닌 자에게 유증등을 한 재산가액 (제24조제1호)
        renounced_inheritance:     선순위 상속인의 포기로 후순위 상속인이 받은 재산가액 (제24조제2호)
        pre_gift_added:            과세가액에 가산한 증여재산가액(증여재산공제 차감 후) (제24조제3호)
        timely_filing:             제67조 기한 내 신고 여부. True 면 신고세액공제 적용.
        skipped_generation_amount: 세대를 건너뛴 상속인(피상속인의 자녀를 제외한 직계비속)이 받았거나 받을 재산가액 (제27조, 원).
                                   대습상속(민법 제1001조)으로 받은 재산은 넣지 않는다. 기본 0(할증 없음).
        skipped_generation_minor:  그 상속인이 미성년자인지 여부. 미성년이고 받은 재산이 20억원을 넘으면 40%.

    Returns:
        {gross_estate, deductions, taxable_base, tax, filing_credit,
         tax_after_filing_credit, policy_version, trace}
        tax 는 상속세산출세액이다.
    """
    trace = CalcTrace(
        tool="tax.kr_inheritance",
        formula=(
            "general = max(lump_sum, basic + personal) | basic + personal; "
            "spouse = max(5억, min(실제, 법정상속분 한도, 30억)); "
            "total = min(general + spouse, 과세가액 - 유증등 - 상속포기분 - 사전증여); "
            "taxable = gross_estate - total; "
            "tax = 누진세율 적용(taxable); "
            "filing_credit = tax x 3%"
        ),
    )

    policy_enum = _parse_rounding(rounding)
    gross       = _non_negative("gross_estate", gross_estate)
    spouse_amt  = _non_negative("spouse_inheritance", spouse_inheritance)
    bequest     = _non_negative("bequest_to_non_heirs", bequest_to_non_heirs)
    renounced   = _non_negative("renounced_inheritance", renounced_inheritance)
    pre_gift    = _non_negative("pre_gift_added", pre_gift_added)
    legal_cap   = (
        _non_negative("spouse_legal_share_cap", spouse_legal_share_cap)
        if spouse_legal_share_cap is not None else None
    )

    if spouse_amt > gross:
        raise InvalidInputError("spouse_inheritance는 gross_estate를 초과할 수 없습니다.")
    for name, count in (
        ("children_count",            children_count),
        ("minor_years_total",         minor_years_total),
        ("elderly_count",             elderly_count),
        ("disabled_life_years_total", disabled_life_years_total),
    ):
        if count < 0:
            raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")

    spouse_present = has_spouse if has_spouse is not None else spouse_amt > Decimal("0")
    if not spouse_present and spouse_amt > Decimal("0"):
        raise InvalidInputError("has_spouse=False 인데 spouse_inheritance가 0보다 큽니다.")
    if spouse_sole_heir and not spouse_present:
        raise InvalidInputError("spouse_sole_heir=True 는 배우자가 있어야 합니다.")

    policy_doc = policy_load("tax", "kr_inheritance", year)
    data       = policy_doc["data"]
    brackets   = data["brackets"]
    deductions = data["deductions"]
    pv         = policy_doc["policy_version"]

    trace.input("gross_estate",              gross_estate)
    trace.input("spouse_inheritance",        spouse_inheritance)
    trace.input("year",                      year)
    trace.input("use_lump_sum",              use_lump_sum)
    trace.input("has_spouse",                spouse_present)
    trace.input("spouse_legal_share_cap",    spouse_legal_share_cap)
    trace.input("spouse_sole_heir",          spouse_sole_heir)
    trace.input("children_count",            children_count)
    trace.input("minor_years_total",         minor_years_total)
    trace.input("elderly_count",             elderly_count)
    trace.input("disabled_life_years_total", disabled_life_years_total)
    trace.input("bequest_to_non_heirs",      bequest_to_non_heirs)
    trace.input("renounced_inheritance",     renounced_inheritance)
    trace.input("pre_gift_added",            pre_gift_added)
    trace.input("timely_filing",             timely_filing)

    personal   = _personal_deduction(
        deductions["personal"], children_count, minor_years_total,
        elderly_count, disabled_life_years_total,
    )
    basic_plus = D(str(deductions["basic"])) + personal
    lump_sum   = D(str(deductions["lump_sum"]))
    if use_lump_sum and not spouse_sole_heir:
        general_deduct = lump_sum if lump_sum > basic_plus else basic_plus
    else:
        general_deduct = basic_plus

    spouse_deduct = _resolve_spouse_deduction(spouse_present, spouse_amt, legal_cap, deductions)

    pre_gift_cut = pre_gift if gross > D(str(data["pre_gift_limit_threshold"])) else Decimal("0")
    limit        = gross - bequest - renounced - pre_gift_cut
    if limit < Decimal("0"):
        limit = Decimal("0")
    requested    = general_deduct + spouse_deduct
    total_deduct = requested if requested < limit else limit

    taxable = gross - total_deduct
    if taxable < Decimal("0"):
        taxable = Decimal("0")

    computed_tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        taxable, brackets, policy_enum, decimals
    )

    skipped = _non_negative("skipped_generation_amount", skipped_generation_amount)
    if skipped > gross:
        raise InvalidInputError("skipped_generation_amount는 상속세 과세가액(gross_estate)을 넘을 수 없습니다.")
    surcharge = Decimal("0")
    if skipped > Decimal("0") and gross > Decimal("0"):
        skip_cfg  = data["generation_skip_surcharge"]
        large     = skipped_generation_minor and skipped > D(str(skip_cfg["minor_large_estate_threshold"]))
        rate      = D(str(skip_cfg["minor_large_estate_rate"] if large else skip_cfg["rate"]))
        surcharge = round_apply(computed_tax * skipped / gross * rate, decimals, policy_enum)
    tax = computed_tax + surcharge
    filing_credit = (
        round_apply(tax * D(str(data["filing_credit_rate"])), decimals, policy_enum)
        if timely_filing else Decimal("0")
    )

    deduct_detail: InheritanceDeductions = {
        "general":   str(general_deduct),
        "personal":  str(personal),
        "spouse":    str(spouse_deduct),
        "requested": str(requested),
        "limit":     str(limit),
        "total":     str(total_deduct),
    }

    trace.step("deductions",    deduct_detail)
    trace.step("taxable_base",  str(taxable))
    trace.step("breakdown",     breakdown)
    trace.step("computed_tax",              str(computed_tax))
    trace.step("generation_skip_surcharge", str(surcharge))
    trace.step("filing_credit", str(filing_credit))
    trace.output(str(tax))

    resp: dict[str, Any] = {
        "gross_estate":            str(gross),
        "deductions":              deduct_detail,
        "taxable_base":            str(taxable),
        "computed_tax":            str(computed_tax),
        "generation_skip_surcharge": str(surcharge),
        "tax":                     str(tax),
        "filing_credit":           str(filing_credit),
        "tax_after_filing_credit": str(tax - filing_credit),
        "effective_rate":          str(eff_rate),
        "marginal_rate":           str(marginal_rate),
        "breakdown":               breakdown,
        "policy_version":          pv,
        "trace":                   trace.to_dict(),
    }
    return cast(TaxKrInheritanceResult, enrich_response(resp, policy_doc))
