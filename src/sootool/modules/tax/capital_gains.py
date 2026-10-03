"""Korean capital gains tax (양도소득세) calculator.

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

계산 순서 (소득세법 제89조, 제95조, 제103조, 제104조 및 같은 법 시행령):
  1. 양도차익 = 양도가액 - 취득가액
  2. 1세대1주택 비과세(양도가액 12억원 이하, 보유 2년 이상, 취득 당시 조정대상지역이면 거주 2년 이상).
     12억원 초과 고가주택은 양도차익과 장기보유특별공제액에 (양도가액 - 12억원) / 양도가액 을 곱한다.
  3. 장기보유 특별공제: 보유 3년 이상. 1세대1주택(거주 2년 이상)은 표 2(보유 + 거주), 그 밖은 표 1.
     미등기양도자산, 분양권, 다주택 중과 대상 주택은 공제하지 않는다.
  4. 양도소득금액 - 양도소득 기본공제(연 250만원, 미등기 제외) = 과세표준
  5. 해당하는 세율(기본세율, 단기보유, 분양권, 비사업용 토지 가산, 미등기, 다주택 중과)별 산출세액 중 큰 것
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ASSET_TYPES      = ("land_building", "housing", "presale_right")
_SURCHARGE_LEVELS = ("none", "two_houses", "three_plus")


def _lookup_ltct_rate(
    holding_years: int,
    table:         list[dict[str, Any]],
) -> Decimal:
    """Look up the LTCT deduction rate from the policy table."""
    for entry in table:
        min_y = entry["holding_years_min"]
        max_y = entry["holding_years_max"]  # None means no upper limit

        if holding_years < min_y:
            continue
        if max_y is None or holding_years <= max_y:
            return D(str(entry["rate"]))

    return Decimal("0")


def _shift_brackets(brackets: list[dict[str, Any]], add: Decimal) -> list[dict[str, Any]]:
    """기본세율 구간에 가산 세율을 더한 구간 (비사업용 토지, 다주택 중과)."""
    return [{"upper": b["upper"], "rate": D(str(b["rate"])) + add} for b in brackets]


def _flat(base: Decimal, rate: Decimal, decimals: int) -> Decimal:
    return round_apply(base * rate, decimals, RoundingPolicy.HALF_UP)


def _parse_transfer_date(transfer_date: str | None, year: int) -> date | None:
    if transfer_date is None:
        return None
    try:
        parsed = date.fromisoformat(transfer_date)
    except ValueError as exc:
        raise InvalidInputError(f"transfer_date는 YYYY-MM-DD 형식이어야 합니다: {transfer_date!r}") from exc
    if parsed.year != year:
        raise InvalidInputError("transfer_date의 연도는 year와 같아야 합니다.")
    return parsed


def _resolve_asset_type(
    asset_type:            str | None,
    is_one_house:          bool,
    multi_house_surcharge: str,
    is_non_business_land:  bool,
) -> str:
    kind = asset_type if asset_type is not None else (
        "housing" if is_one_house or multi_house_surcharge != "none" else "land_building"
    )
    if kind not in _ASSET_TYPES:
        raise InvalidInputError(f"asset_type은 {list(_ASSET_TYPES)} 중 하나여야 합니다: {kind!r}")
    if (is_one_house or multi_house_surcharge != "none") and kind != "housing":
        raise InvalidInputError("is_one_house 또는 multi_house_surcharge 는 asset_type='housing' 에만 적용됩니다.")
    if is_non_business_land and kind != "land_building":
        raise InvalidInputError("is_non_business_land 는 asset_type='land_building' 에만 적용됩니다.")
    return kind


def _surcharge_rate(
    level:         str,
    holding_years: int,
    transfer_on:   date | None,
    rule:          Mapping[str, Any],
    trace:         CalcTrace,
) -> Decimal:
    """법 제104조제7항 가산 세율. 중과 제외 또는 한시 완화를 반영한다. 0 이면 중과하지 않는다."""
    if level == "none":
        return Decimal("0")

    exclusion = rule.get("exclusion")
    if exclusion is not None and holding_years >= int(exclusion["min_holding_years"]):
        if transfer_on is None:
            raise InvalidInputError(
                "보유기간이 2년 이상인 다주택 중과 판정에는 transfer_date(양도일)가 필요합니다."
            )
        until = date.fromisoformat(str(exclusion["transfer_until"]))
        if transfer_on <= until:
            trace.step("multi_house_surcharge_excluded", f"양도일 {transfer_on.isoformat()} <= {until.isoformat()}")
            return Decimal("0")

    relief = rule.get("relief")
    if relief is not None and holding_years >= int(relief["min_holding_years"]):
        rate = D(str(relief[level]))
        trace.step("multi_house_surcharge_relief", str(rate))
        return rate

    return D(str(rule[level]))


@REGISTRY.tool(
    namespace="tax",
    name="capital_gains_kr",
    description=(
        "한국 양도소득세 계산. 1세대1주택 비과세와 고가주택 안분, 장기보유특별공제(표 1, 표 2 보유·거주), "
        "양도소득 기본공제, 단기보유·분양권·비사업용 토지·미등기·조정대상지역 다주택 중과 세율. "
        "소득세법 제89조·제95조·제103조·제104조 기준."
    ),
    version="2.0.0",
    policy=True,
)
def tax_capital_gains_kr(
    acquisition_price:          str,
    sale_price:                 str,
    holding_years:              int,
    is_one_house:               bool,
    year:                       int,
    decimals:                   int = 0,
    residence_years:            int | None = None,
    acquired_in_regulated_area: bool = False,
    asset_type:                 str | None = None,
    is_non_business_land:       bool = False,
    is_unregistered:            bool = False,
    multi_house_surcharge:      str = "none",
    transfer_date:              str | None = None,
    apply_basic_deduction:      bool = True,
) -> dict[str, Any]:
    """Calculate Korean capital gains tax.

    Args:
        acquisition_price:          취득가액 (Decimal string, 원)
        sale_price:                 양도가액 (Decimal string, 원)
        holding_years:              보유 기간 (년, 정수, 1년 미만 버림)
        is_one_house:               1세대1주택 여부
        year:                       과세연도
        decimals:                   소수점 자리수 (기본 0)
        residence_years:            보유기간 중 거주 기간 (년). 생략하면 보유기간과 같다고 본다
        acquired_in_regulated_area: 취득 당시 조정대상지역 주택 여부 (비과세 거주 요건)
        asset_type:                 land_building(주택 외 토지·건물) | housing(주택) | presale_right(분양권).
                                    생략하면 1세대1주택·다주택 중과 입력이면 housing, 그 밖은 land_building
        is_non_business_land:       비사업용 토지 여부 (기본세율 + 10%p)
        is_unregistered:            미등기양도자산 여부 (70%, 공제·비과세 배제)
        multi_house_surcharge:      none | two_houses | three_plus. 조정대상지역 1세대 2주택·3주택 이상 중과 대상
        transfer_date:              양도일 (YYYY-MM-DD). 중과 제외 기한 판정에 사용
        apply_basic_deduction:      양도소득 기본공제 적용 여부 (같은 해 다른 양도에서 이미 공제했으면 False)

    Returns:
        {gain, exempt, taxable_portion_gain, ltct_rate, ltct_deduction, taxable_gain, basic_deduction,
         tax_base, applied_rate, rate_candidates, tax, policy_version, trace}
        taxable_gain 은 양도소득금액(과세 대상 양도차익 - 장기보유 특별공제액)이다.
    """
    trace = CalcTrace(
        tool="tax.capital_gains_kr",
        formula=(
            "gain = sale - acquisition; 비과세·고가주택 안분; "
            "taxable_gain = 과세대상 양도차익 - 장기보유특별공제; "
            "tax_base = taxable_gain - 기본공제; tax = max(해당 세율별 산출세액)"
        ),
    )

    acq  = D(acquisition_price)
    sale = D(sale_price)

    if acq < Decimal("0"):
        raise InvalidInputError("acquisition_price는 0 이상이어야 합니다.")
    if sale < Decimal("0"):
        raise InvalidInputError("sale_price는 0 이상이어야 합니다.")
    if holding_years < 0:
        raise InvalidInputError("holding_years는 0 이상이어야 합니다.")
    if residence_years is not None and not (0 <= residence_years <= holding_years):
        raise InvalidInputError("residence_years는 0 이상 holding_years 이하여야 합니다.")
    if multi_house_surcharge not in _SURCHARGE_LEVELS:
        raise InvalidInputError(f"multi_house_surcharge는 {list(_SURCHARGE_LEVELS)} 중 하나여야 합니다.")
    if is_one_house and multi_house_surcharge != "none":
        raise InvalidInputError("is_one_house 와 multi_house_surcharge 는 함께 지정할 수 없습니다.")
    kind        = _resolve_asset_type(asset_type, is_one_house, multi_house_surcharge, is_non_business_land)
    transfer_on = _parse_transfer_date(transfer_date, year)

    policy_doc = policy_load("tax", "kr_capital_gains", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]
    brackets   = data["income_tax_brackets"]

    residence = holding_years if residence_years is None else residence_years

    trace.input("acquisition_price",          acquisition_price)
    trace.input("sale_price",                 sale_price)
    trace.input("holding_years",              holding_years)
    trace.input("is_one_house",               is_one_house)
    trace.input("year",                       year)
    trace.input("residence_years",            residence_years)
    trace.input("acquired_in_regulated_area", acquired_in_regulated_area)
    trace.input("asset_type",                 kind)
    trace.input("is_non_business_land",       is_non_business_land)
    trace.input("is_unregistered",            is_unregistered)
    trace.input("multi_house_surcharge",      multi_house_surcharge)
    trace.input("transfer_date",              transfer_date)
    trace.input("apply_basic_deduction",      apply_basic_deduction)
    if is_one_house and residence_years is None:
        trace.step("assumption", "residence_years 생략: 거주기간을 보유기간과 같다고 본다")

    gain = sale - acq
    trace.step("gain", str(gain))

    def _zero(exempt: bool) -> dict[str, Any]:
        trace.output("0")
        resp0 = {
            "gain":                 str(gain),
            "exempt":               exempt,
            "taxable_portion_gain": "0",
            "ltct_rate":            "0",
            "ltct_deduction":       "0",
            "taxable_gain":         "0",
            "basic_deduction":      "0",
            "tax_base":             "0",
            "applied_rate":         None,
            "rate_candidates":      [],
            "tax":                  "0",
            "policy_version":       pv,
            "trace":                trace.to_dict(),
        }
        return enrich_response(resp0, policy_doc)

    if gain <= Decimal("0"):
        return _zero(False)

    # 1세대1주택 비과세와 고가주택 안분 (법 제89조제1항제3호, 시행령 제154조제1항·제160조제1항)
    portion = Decimal("1")
    if is_one_house and not is_unregistered:
        rule      = data["one_house_exemption"]
        threshold = D(str(rule["sale_price_threshold"]))
        eligible  = holding_years >= int(rule["min_holding_years"]) and (
            not acquired_in_regulated_area
            or residence >= int(rule["min_residence_years_if_acquired_in_regulated_area"])
        )
        trace.step("one_house_exemption_eligible", eligible)
        if eligible:
            if sale <= threshold:
                trace.step("one_house_exemption", f"양도가액 {sale} <= {threshold}: 비과세")
                return _zero(True)
            portion = (sale - threshold) / sale
            trace.step("high_value_house_ratio", str(portion))

    taxable_portion = gain * portion
    trace.step("taxable_portion_gain", str(taxable_portion))

    surcharge = (
        _surcharge_rate(multi_house_surcharge, holding_years, transfer_on, data["multi_house_surcharge"], trace)
        if kind == "housing" else Decimal("0")
    )
    trace.step("multi_house_surcharge_rate", str(surcharge))

    # 장기보유 특별공제 (법 제95조제2항, 시행령 제159조의4)
    min_res = int(data["one_house_min_residence_years"])
    if is_unregistered or surcharge > Decimal("0") or kind == "presale_right" or holding_years < 3:
        ltct_rate = Decimal("0")
        trace.step("ltct_table", "none")
    elif is_one_house and residence >= min_res:
        holding_part   = _lookup_ltct_rate(holding_years, data["one_house_holding"])
        residence_part = _lookup_ltct_rate(residence, data["one_house_residence"])
        ltct_rate      = holding_part + residence_part
        trace.step("ltct_table", "one_house")
        trace.step("ltct_holding_rate", str(holding_part))
        trace.step("ltct_residence_rate", str(residence_part))
    else:
        ltct_rate = _lookup_ltct_rate(holding_years, data["general"])
        trace.step("ltct_table", "general")

    ltct_deduct = taxable_portion * ltct_rate
    income      = taxable_portion - ltct_deduct
    trace.step("ltct_rate",      str(ltct_rate))
    trace.step("ltct_deduction", str(ltct_deduct))
    trace.step("taxable_gain",   str(income))

    # 양도소득 기본공제 (법 제103조제1항, 미등기 제외)
    basic = Decimal("0")
    if apply_basic_deduction and not is_unregistered:
        basic = D(str(data["basic_deduction"]))
        long_res = data.get("basic_deduction_long_residence_one_house")
        if (
            long_res is not None and is_one_house
            and residence >= int(long_res["min_residence_years"])
            and sale <= D(str(long_res["max_sale_price"]))
        ):
            basic = D(str(long_res["amount"]))
            trace.step("basic_deduction_rule", "long_residence_one_house")
        basic = min(basic, income)
    tax_base = income - basic
    trace.step("basic_deduction", str(basic))
    trace.step("tax_base",        str(tax_base))

    # 세율 후보 (법 제104조제1항 후단, 제7항 후단: 둘 이상 해당하면 산출세액 중 큰 것)
    candidates: list[tuple[str, Decimal]] = []
    if is_unregistered:
        candidates.append(("unregistered", _flat(tax_base, D(str(data["unregistered_rate"])), decimals)))
    if kind == "presale_right":
        candidates.append(("presale_right", _flat(tax_base, D(str(data["presale_right_rate"])), decimals)))
    else:
        add = surcharge + (D(str(data["non_business_land_surcharge"])) if is_non_business_land else Decimal("0"))
        label = "basic" if add == Decimal("0") else (
            "multi_house_surcharge" if surcharge > Decimal("0") else "non_business_land"
        )
        rated = brackets if add == Decimal("0") else _shift_brackets(brackets, add)
        progressive_tax, _, _, _ = _calc_progressive(tax_base, rated, RoundingPolicy.HALF_UP, decimals)
        candidates.append((label, progressive_tax))
    if holding_years < 2:
        short = data["short_term_rates"][kind]
        key   = "under_1y" if holding_years < 1 else "under_2y"
        candidates.append((f"short_term_{key}", _flat(tax_base, D(str(short[key])), decimals)))

    applied_rate, tax = max(candidates, key=lambda c: c[1])
    trace.step("rate_candidates", {name: str(value) for name, value in candidates})
    trace.step("applied_rate",    applied_rate)
    trace.output(str(tax))

    resp = {
        "gain":                 str(gain),
        "exempt":               False,
        "taxable_portion_gain": str(taxable_portion),
        "ltct_rate":            str(ltct_rate),
        "ltct_deduction":       str(ltct_deduct),
        "taxable_gain":         str(income),
        "basic_deduction":      str(basic),
        "tax_base":             str(tax_base),
        "applied_rate":         applied_rate,
        "rate_candidates":      [{"rate": name, "tax": str(value)} for name, value in candidates],
        "tax":                  str(tax),
        "policy_version":       pv,
        "trace":                trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
