"""Korean simplified taxpayer VAT (간이과세자 부가가치세) calculator.

Author: 최진호
Date: 2026-04-24

부가가치세법 제61조·제63조 간이과세 납부세액 계산:
  납부세액 = 공급대가 × 업종별 부가가치율 × 10%

업종 구분 (부가가치세법 시행령 §111 별표, 2021.7.1 이후):
  retail/sales/food_service   15%
  manufacturing               20%
  accommodation               25%
  construction                30%
  financial                   40%
  other_services              30%

기타 규정:
  - 연간 공급대가 4,800만원 미만: 납부면제 (부가세법 §69)
  - 직전연도 공급대가 1억 4백만원 이상: 간이과세 대상 아님 → 일반과세 전환 필요
  - 매입세금계산서 수령분: 공제 가능 (공급가액 × 부가가치율 × 10%)
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
    namespace="tax",
    name="kr_simplified_vat",
    description=(
        "한국 간이과세자 부가가치세 계산 (부가세법 §61·§63). "
        "업종별 부가가치율 × 10%를 공급대가에 적용. "
        "4,800만원 미만 납부 면제 처리."
    ),
    version="1.0.0",
)
def tax_kr_simplified_vat(
    supply_value:     str,
    business_type:    str,
    year:             int,
    input_tax_amount: str = "0",
) -> dict[str, Any]:
    """Calculate simplified-taxpayer VAT.

    Args:
        supply_value:     과세기간 공급대가(공급가액 + 부가세) 합계, 원.
        business_type:    업종 코드. retail/sales/food_service/manufacturing/
                         accommodation/construction/financial/other_services.
        year:             과세연도.
        input_tax_amount: 매입세금계산서 공급가액(원), 공제세액 산정용.

    Returns:
        {supply_value, business_type, value_added_rate, vat_payable, input_credit,
         net_payable, threshold_exceeded, nonpayment_exempt, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_simplified_vat",
        formula=(
            "납부세액 = 공급대가 × 부가가치율 × 10%; "
            "공제세액 = 매입공급가액 × 부가가치율 × 10%; "
            "최종 = max(0, 납부세액 - 공제세액); "
            "공급대가 < 4,800만원 → 면제"
        ),
    )

    supply = D(supply_value)
    inputs = D(input_tax_amount)

    if supply < Decimal("0"):
        raise InvalidInputError("supply_value는 0 이상이어야 합니다.")
    if inputs < Decimal("0"):
        raise InvalidInputError("input_tax_amount는 0 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_simplified_vat", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    rates_map: dict[str, Any] = data["value_added_rates"]
    if business_type not in rates_map:
        raise InvalidInputError(
            f"business_type은 {sorted(rates_map.keys())} 중 하나여야 합니다."
        )

    trace.input("supply_value",     supply_value)
    trace.input("business_type",    business_type)
    trace.input("year",             year)
    trace.input("input_tax_amount", input_tax_amount)

    va_rate  = D(str(rates_map[business_type]))
    vat_rate = D(str(data["vat_rate"]))

    threshold    = D(str(data["threshold_amount"]))
    nonpay_thr   = D(str(data["nonpayment_threshold"]))

    threshold_exceeded = supply >= threshold
    nonpayment_exempt  = supply < nonpay_thr

    vat_payable  = round_apply(supply * va_rate * vat_rate, 0, RoundingPolicy.DOWN)
    input_credit = round_apply(inputs * va_rate * vat_rate, 0, RoundingPolicy.DOWN)

    if nonpayment_exempt:
        net_payable = Decimal("0")
    else:
        raw_net = vat_payable - input_credit
        net_payable = raw_net if raw_net > Decimal("0") else Decimal("0")

    trace.step("value_added_rate",   str(va_rate))
    trace.step("vat_rate",           str(vat_rate))
    trace.step("threshold_exceeded", threshold_exceeded)
    trace.step("nonpayment_exempt",  nonpayment_exempt)
    trace.step("vat_payable",        str(vat_payable))
    trace.step("input_credit",       str(input_credit))
    trace.output(str(net_payable))

    resp: dict[str, Any] = {
        "supply_value":        str(supply),
        "business_type":       business_type,
        "value_added_rate":    str(va_rate),
        "vat_payable":         str(vat_payable),
        "input_credit":        str(input_credit),
        "net_payable":         str(net_payable),
        "threshold_exceeded":  threshold_exceeded,
        "nonpayment_exempt":   nonpayment_exempt,
        "policy_version":      pv,
        "trace":               trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
