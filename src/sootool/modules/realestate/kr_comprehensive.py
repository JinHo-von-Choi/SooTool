"""Korean comprehensive real-estate holding tax (종합부동산세, 종부세법 §8~§10).

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03

계산 순서
1. 납세의무 기준(정책에 taxpayer_threshold 가 있으면) 미만이면 0
2. 과세표준 = (공시가격 합계 - 기본공제) × 공정시장가액비율
3. 산출세액 = 누진세율(2주택 이하 / 3주택 이상) 또는 법인 단일세율
4. 재산세 상당액 공제(§9③, 시행령 §4의3)
5. 1세대 1주택자 연령·보유(거주) 세액공제(§9⑤~)
6. 세부담상한(§10): 직전 연도 총세액상당액이 주어지면 적용(법인 단일세율 제외)
7. 농어촌특별세 = 납부할 종부세 × 20%
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
from sootool.modules.realestate._kr_local_tax import lookup_upper_table
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO = Decimal("0")


def _floor_won(value: Decimal) -> Decimal:
    return round_apply(value, 0, RoundingPolicy.FLOOR)


def _threshold_rate(table: list[dict[str, Any]] | None, value: int | None) -> Decimal:
    """``min`` 이상인 행 중 가장 큰 기준의 공제율. 값이 없거나 해당 행이 없으면 0."""
    if not table or value is None:
        return _ZERO
    rate = _ZERO
    for row in sorted(table, key=lambda r: int(r["min"])):
        if value >= int(row["min"]):
            rate = D(str(row["rate"]))
    return rate


def _deduction(
    cfg:                   dict[str, Any],
    total:                 Decimal,
    is_one_house:          bool,
    is_corporate:          bool,
    resident_house_price:  Decimal | None,
) -> Decimal:
    """기본공제(종부세법 제8조제1항)."""
    if is_corporate:
        return D(str(cfg.get("corporate", 0)))
    resident = resident_house_price is not None and resident_house_price > _ZERO
    if is_one_house:
        if resident and cfg.get("one_house_resident") is not None:
            return D(str(cfg["one_house_resident"]))
        return D(str(cfg["one_house"]))
    if cfg.get("multi_house_resident_share") is not None:
        share = min(resident_house_price, total) / total if resident and resident_house_price else _ZERO
        return D(str(cfg["multi_house_base"])) + D(str(cfg["multi_house_resident_share"])) * share
    return D(str(cfg["multi_house"]))


def _property_tax_credit(
    cfg:          dict[str, Any],
    total:        Decimal,
    taxable:      Decimal,
    is_one_house: bool,
    levied:       Decimal | None,
) -> tuple[Decimal, Decimal, Decimal]:
    """재산세 상당액 공제액(시행령 제4조의3제1항)과 (부과 재산세, 분모)를 반환한다.

    공제액 = 부과 재산세 × (종부세 과세표준 × 재산세 공정시장가액비율 × 표준세율)
             / 주택을 합산하여 표준세율로 계산한 재산세 상당액.
    부과 재산세가 주어지지 않으면 분모(합산 표준세율 재산세)를 부과 재산세로 본다.
    """
    one_house_table = cfg.get("one_house_fair_market_ratio")
    if is_one_house and one_house_table:
        prop_fmr = lookup_upper_table(total, one_house_table, "ratio")
    else:
        prop_fmr = D(str(cfg["fair_market_ratio"]))
    numerator = taxable * prop_fmr * D(str(cfg["standard_rate"]))
    denominator, _e, _m, _b = _calc_progressive(total * prop_fmr, cfg["brackets"], RoundingPolicy.HALF_UP, 0)
    levied_tax = levied if levied is not None else denominator
    if denominator <= _ZERO:
        return _ZERO, levied_tax, denominator
    return _floor_won(levied_tax * numerator / denominator), levied_tax, denominator


def _one_house_credit(
    cfg:             dict[str, Any] | None,
    tax:             Decimal,
    age:             int | None,
    holding_years:   int | None,
    residence_years: int | None,
) -> tuple[Decimal, Decimal]:
    """1세대 1주택자 세액공제액과 적용 공제율을 반환한다."""
    if not cfg or tax <= _ZERO:
        return _ZERO, _ZERO
    age_rate       = _threshold_rate(cfg.get("age"), age)
    holding_rate   = _threshold_rate(cfg.get("holding"), holding_years)
    residence_rate = _threshold_rate(cfg.get("residence"), residence_years)
    total_rate     = min(age_rate + max(holding_rate, residence_rate), D(str(cfg["max_total_rate"])))
    credit         = _floor_won(tax * total_rate)
    if cfg.get("max_amount") is not None:
        credit = min(credit, D(str(cfg["max_amount"])))
    return credit, total_rate


def _non_negative_int(name: str, value: int | None) -> None:
    if value is not None and value < 0:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")


def _optional_amount(name: str, value: str | None) -> Decimal | None:
    if value is None:
        return None
    amount = D(value)
    if amount < _ZERO:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


@REGISTRY.tool(
    namespace="realestate",
    name="kr_comprehensive",
    description=(
        "주택분 종합부동산세 계산 (종부세법 §8~§10). 기본공제 후 공정시장가액비율 적용, "
        "2주택 이하/3주택 이상 누진세율 또는 법인 단일세율, 재산세 상당액 공제, "
        "1세대 1주택자 연령·보유 세액공제, 세부담상한(직전 연도 세액 입력 시), 농어촌특별세 20% 합산."
    ),
    version="1.1.0",
    policy=True,
)
def realestate_kr_comprehensive(
    total_published_price: str,
    year:                  int,
    house_count:           int,
    is_corporate:          bool       = False,
    age:                   int | None = None,
    holding_years:         int | None = None,
    residence_years:       int | None = None,
    resident_house_price:  str | None = None,
    property_tax_levied:   str | None = None,
    prior_year_total_tax:  str | None = None,
) -> dict[str, Any]:
    """Calculate comprehensive real-estate tax (종부세, 주택분).

    Args:
        total_published_price: 보유 주택 공시가격 합계 (원)
        year:                  과세연도
        house_count:           납세의무자 보유 주택 수 (1이면 1세대 1주택자로 본다)
        is_corporate:          법인(종부세법 제9조제2항제3호 세율 적용) 여부
        age:                   과세기준일 현재 만 나이 (1세대 1주택자 연령 공제)
        holding_years:         과세기준일 현재 보유기간(년) (1세대 1주택자 보유 공제)
        residence_years:       과세기준일 현재 거주기간(년) (거주기간 공제가 있는 연도에만 사용)
        resident_house_price:  거주하는 주택의 공시가격 (거주 여부로 공제가 달라지는 연도에만 사용)
        property_tax_levied:   과세표준합산주택에 부과된 재산세 합계(도시지역분 제외).
                               생략하면 합산 표준세율 재산세로 본다
        prior_year_total_tax:  직전 연도 주택 총세액상당액(재산세 + 종부세). 주어지면 세부담상한 적용

    Returns:
        {published_price, deduction, taxable_base, base_tax, property_tax_credit,
         one_house_credit, burden_cap_reduction, comprehensive_tax, rural_tax, total_tax,
         breakdown, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_comprehensive",
        formula=(
            "과세표준 = (공시가격 합계 - 기본공제) × 공정시장가액비율; "
            "산출세액 = 누진세율(과세표준) 또는 법인 단일세율; "
            "종부세 = 산출세액 - 재산세 상당액 공제 - 1세대 1주택 세액공제 - 세부담상한 초과분; "
            "농어촌특별세 = 종부세 × 20%"
        ),
    )

    pp = D(total_published_price)
    if pp <= _ZERO:
        raise InvalidInputError("total_published_price는 0보다 커야 합니다.")
    if house_count < 1:
        raise InvalidInputError("house_count는 1 이상이어야 합니다.")
    _non_negative_int("age", age)
    _non_negative_int("holding_years", holding_years)
    _non_negative_int("residence_years", residence_years)
    resident_price = _optional_amount("resident_house_price", resident_house_price)
    levied         = _optional_amount("property_tax_levied", property_tax_levied)
    prior_total    = _optional_amount("prior_year_total_tax", prior_year_total_tax)

    policy_doc = policy_load("realestate", "kr_comprehensive", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("total_published_price", total_published_price)
    trace.input("year",                  year)
    trace.input("house_count",           house_count)
    trace.input("is_corporate",          is_corporate)
    trace.input("age",                   age)
    trace.input("holding_years",         holding_years)
    trace.input("residence_years",       residence_years)
    trace.input("resident_house_price",  resident_house_price)
    trace.input("property_tax_levied",   property_tax_levied)
    trace.input("prior_year_total_tax",  prior_year_total_tax)

    is_one_house = house_count == 1 and not is_corporate
    deduction    = _deduction(data["base_deduction"], pp, is_one_house, is_corporate, resident_price)

    threshold_cfg = data.get("taxpayer_threshold")
    threshold: Decimal | None = None
    if threshold_cfg:
        key       = "corporate" if is_corporate else ("one_house" if is_one_house else "multi_house")
        threshold = D(str(threshold_cfg[key]))

    after_deduct = pp - deduction
    if (threshold is not None and pp <= threshold) or after_deduct <= _ZERO:
        trace.step("taxpayer_threshold", str(threshold) if threshold is not None else None)
        trace.step("deduction",          str(deduction))
        trace.step("after_deduct",       str(after_deduct))
        trace.output("0")
        resp: dict[str, Any] = {
            "published_price":      str(pp),
            "deduction":            str(deduction),
            "taxable_base":         "0",
            "base_tax":             "0",
            "property_tax_credit":  "0",
            "one_house_credit":     "0",
            "burden_cap_reduction": "0",
            "comprehensive_tax":    "0",
            "rural_tax":            "0",
            "total_tax":            "0",
            "breakdown":            [],
            "policy_version":       pv,
            "trace":                trace.to_dict(),
        }
        return enrich_response(resp, policy_doc)

    fmr_ratio = D(str(data["fair_market_ratio"]))
    taxable   = after_deduct * fmr_ratio

    multi_min = int(data.get("multi_bracket_min_house_count", 3))
    breakdown: list[dict[str, Any]]
    if is_corporate:
        rates     = data["corporate_rates"]
        corp_rate = D(str(rates["three_plus"] if house_count >= multi_min else rates["two_or_fewer"]))
        base_tax  = round_apply(taxable * corp_rate, 0, RoundingPolicy.HALF_UP)
        breakdown = [{"corporate_rate": str(corp_rate), "tax": str(base_tax)}]
        rate_table = "corporate"
    else:
        rate_table = "three_plus" if house_count >= multi_min else "two_or_fewer"
        brackets   = data["multi_house_brackets"] if rate_table == "three_plus" else data["one_house_brackets"]
        base_tax, _eff, _m, breakdown = _calc_progressive(taxable, brackets, RoundingPolicy.HALF_UP, 0)

    prop_credit, levied_tax, standard_prop_tax = _property_tax_credit(
        data["property_tax_credit"], pp, taxable, is_one_house, levied
    )
    prop_credit = min(prop_credit, base_tax)
    after_prop  = base_tax - prop_credit

    one_credit, one_rate = (
        _one_house_credit(data.get("one_house_credit"), after_prop, age, holding_years, residence_years)
        if is_one_house else (_ZERO, _ZERO)
    )
    comprehensive = after_prop - one_credit

    cap_reduction = _ZERO
    if prior_total is not None and not is_corporate and data.get("burden_cap_ratio") is not None:
        cap_amount = prior_total * D(str(data["burden_cap_ratio"]))
        excess     = levied_tax + comprehensive - cap_amount
        if excess > _ZERO:
            cap_reduction = min(round_apply(excess, 0, RoundingPolicy.CEIL), comprehensive)
            comprehensive = comprehensive - cap_reduction

    rural_rate = D(str(data["rural_special_rate"]))
    rural_tax  = _floor_won(comprehensive * rural_rate)
    total      = comprehensive + rural_tax

    trace.step("deduction",            str(deduction))
    trace.step("taxable_base",         str(taxable))
    trace.step("rate_table",           rate_table)
    trace.step("base_tax",             str(base_tax))
    trace.step("breakdown",            breakdown)
    trace.step("property_tax_levied",  str(levied_tax))
    trace.step("standard_property_tax", str(standard_prop_tax))
    trace.step("property_tax_credit",  str(prop_credit))
    trace.step("one_house_credit_rate", str(one_rate))
    trace.step("one_house_credit",     str(one_credit))
    trace.step("burden_cap_reduction", str(cap_reduction))
    trace.step("comprehensive_tax",    str(comprehensive))
    trace.step("rural_tax",            str(rural_tax))
    trace.output(str(total))

    resp = {
        "published_price":      str(pp),
        "deduction":            str(deduction),
        "taxable_base":         str(taxable),
        "rate_table":           rate_table,
        "base_tax":             str(base_tax),
        "property_tax_credit":  str(prop_credit),
        "property_tax_levied":  str(levied_tax),
        "one_house_credit":     str(one_credit),
        "burden_cap_reduction": str(cap_reduction),
        "comprehensive_tax":    str(comprehensive),
        "rural_tax":            str(rural_tax),
        "total_tax":            str(total),
        "breakdown":            breakdown,
        "policy_version":       pv,
        "trace":                trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
