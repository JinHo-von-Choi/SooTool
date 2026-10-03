"""Korean simplified taxpayer VAT (간이과세자 부가가치세) calculator.

Author: 최진호
Date: 2026-04-24
Modified: 2026-10-03

부가가치세법 제63조 간이과세 납부세액 계산:
  납부세액 = 공급대가 × 업종별 부가가치율 × 10%

업종 구분 (부가가치세법 시행령 제111조제2항 표):
  retail/sales/food_service                         15%
  manufacturing                                     20%
  accommodation                                     25%
  construction/transport_warehousing/
  information_communication                         30%
  financial/real_estate_rental                      40%
  other_services                                    30%

기타 규정:
  - 해당 과세기간 공급대가 4,800만원 미만: 납부의무 면제 (법 제69조제1항)
  - 직전 연도 공급대가 1억4백만원 이상: 간이과세 대상 아님 (법 제61조제1항, 시행령 제109조제1항)
  - 부동산임대업·과세유흥장소: 해당 업종 직전 연도 공급대가 4,800만원 이상이면 간이과세 배제 (법 제61조제1항제3호)
  - 세금계산서등 수취분 공제: 수취 공급대가 × 0.5% (법 제63조제3항제1호)
  - 신용카드 등 매출세액공제: 발급금액 × 공제율, 연간 한도 (법 제46조제1항)
  - 공제 합계가 납부세액을 초과하는 부분은 없는 것으로 본다 (법 제63조제6항)
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

_RESTRICTED_BUSINESS_TYPES = frozenset(["real_estate_rental"])


def _non_negative(name: str, value: str) -> Decimal:
    """금액 입력을 Decimal 로 바꾸고 음수를 거부한다."""
    amount = D(value)
    if amount < Decimal("0"):
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


@REGISTRY.tool(
    namespace="tax",
    name="kr_simplified_vat",
    description=(
        "한국 간이과세자 부가가치세 계산 (부가세법 §46·§61·§63·§69). "
        "업종별 부가가치율 × 10%를 공급대가에 적용. "
        "세금계산서등 수취 공급대가 × 0.5% 공제, 신용카드 등 매출세액공제, "
        "4,800만원 미만 납부 면제 처리."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_simplified_vat(
    supply_value:        str,
    business_type:       str,
    year:                int,
    input_tax_amount:    str        = "0",
    card_sales_amount:   str        = "0",
    prior_year_supply:   str | None = None,
    restricted_business: bool       = False,
) -> dict[str, Any]:
    """Calculate simplified-taxpayer VAT.

    Args:
        supply_value:        과세기간 공급대가(공급가액 + 부가세) 합계, 원.
        business_type:       업종 코드. retail/sales/food_service/manufacturing/
                             accommodation/construction/transport_warehousing/
                             information_communication/financial/real_estate_rental/
                             other_services.
        year:                과세연도.
        input_tax_amount:    해당 과세기간에 세금계산서등을 발급받은 재화·용역의 공급대가 합계(원).
        card_sales_amount:   신용카드매출전표·현금영수증 등 발급금액 또는 전자적 결제금액 합계(원).
                             법 제46조제1항제1호 해당 사업자만 입력한다.
        prior_year_supply:   직전 연도 공급대가 합계(원). 간이과세 기준 판정에 쓴다.
                             생략하면 supply_value 로 판정한다.
        restricted_business: 부동산임대업 또는 과세유흥장소 경영 여부 (법 제61조제1항제3호).
                             business_type=real_estate_rental 이면 자동으로 적용한다.

    Returns:
        {supply_value, business_type, value_added_rate, vat_payable, input_credit,
         card_sales_credit, net_payable, threshold_exceeded, threshold_basis,
         applicable_threshold, nonpayment_exempt, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_simplified_vat",
        formula=(
            "납부세액 = 공급대가 × 부가가치율 × 10%; "
            "공제세액 = 세금계산서등 수취 공급대가 × 0.5%; "
            "카드공제 = min(카드 발급금액 × 공제율, 연간 한도); "
            "최종 = max(0, 납부세액 - 공제세액 - 카드공제); "
            "공급대가 < 4,800만원 → 면제"
        ),
    )

    supply = _non_negative("supply_value", supply_value)
    inputs = _non_negative("input_tax_amount", input_tax_amount)
    card   = _non_negative("card_sales_amount", card_sales_amount)
    prior  = _non_negative("prior_year_supply", prior_year_supply) if prior_year_supply is not None else None

    policy_doc = policy_load("tax", "kr_simplified_vat", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    rates_map: dict[str, Any] = data["value_added_rates"]
    if business_type not in rates_map:
        raise InvalidInputError(
            f"business_type은 {sorted(rates_map.keys())} 중 하나여야 합니다."
        )

    trace.input("supply_value",        supply_value)
    trace.input("business_type",       business_type)
    trace.input("year",                year)
    trace.input("input_tax_amount",    input_tax_amount)
    trace.input("card_sales_amount",   card_sales_amount)
    trace.input("prior_year_supply",   prior_year_supply)
    trace.input("restricted_business", restricted_business)

    va_rate     = D(str(rates_map[business_type]))
    vat_rate    = D(str(data["vat_rate"]))
    credit_rate = D(str(data["input_credit_rate"]))
    card_cfg    = data["card_sales_credit"]

    restricted = restricted_business or business_type in _RESTRICTED_BUSINESS_TYPES
    threshold  = D(str(data["restricted_threshold_amount" if restricted else "threshold_amount"]))
    nonpay_thr = D(str(data["nonpayment_threshold"]))

    threshold_basis    = "prior_year_supply" if prior is not None else "supply_value"
    threshold_exceeded = (prior if prior is not None else supply) >= threshold
    nonpayment_exempt  = supply < nonpay_thr

    vat_payable  = round_apply(supply * va_rate * vat_rate, 0, RoundingPolicy.DOWN)
    input_credit = round_apply(inputs * credit_rate, 0, RoundingPolicy.DOWN)
    card_raw     = card * D(str(card_cfg["rate"]))
    card_limit   = D(str(card_cfg["annual_limit"]))
    card_credit  = round_apply(card_raw if card_raw < card_limit else card_limit, 0, RoundingPolicy.DOWN)

    if nonpayment_exempt:
        net_payable = Decimal("0")
    else:
        raw_net = vat_payable - input_credit - card_credit
        net_payable = raw_net if raw_net > Decimal("0") else Decimal("0")

    trace.step("value_added_rate",     str(va_rate))
    trace.step("vat_rate",             str(vat_rate))
    trace.step("applicable_threshold", str(threshold))
    trace.step("threshold_basis",      threshold_basis)
    trace.step("threshold_exceeded",   threshold_exceeded)
    trace.step("nonpayment_exempt",    nonpayment_exempt)
    trace.step("vat_payable",          str(vat_payable))
    trace.step("input_credit",         str(input_credit))
    trace.step("card_sales_credit",    str(card_credit))
    trace.output(str(net_payable))

    resp: dict[str, Any] = {
        "supply_value":         str(supply),
        "business_type":        business_type,
        "value_added_rate":     str(va_rate),
        "vat_payable":          str(vat_payable),
        "input_credit":         str(input_credit),
        "card_sales_credit":    str(card_credit),
        "net_payable":          str(net_payable),
        "threshold_exceeded":   threshold_exceeded,
        "threshold_basis":      threshold_basis,
        "applicable_threshold": str(threshold),
        "nonpayment_exempt":    nonpayment_exempt,
        "policy_version":       pv,
        "trace":                trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
