"""Korean securities transaction tax (증권거래세) and rural special tax calculator.

작성자: 최진호
작성일: 2026-10-03

증권거래세 (증권거래세법 제7조, 제8조, 시행령 제5조):
  증권거래세 = 양도가액 × 시장별 세율
  기본세율 0.35% (법 제8조제1항). 증권시장 거래 주권은 시행령 제5조 탄력세율.

  양도 연도      유가증권  코스닥·K-OTC  코넥스
  2023           0.05%     0.20%         0.10%
  2024           0.03%     0.18%         0.10%
  2025           0%        0.15%         0.10%
  2026~          0.05%     0.20%         0.10%

농어촌특별세 (농어촌특별세법 제5조제1항제5호, 시행령 제5조제1항):
  유가증권시장 양도가액 × 0.15%. 유가증권시장에 영의 세율이 적용되어도 과세 (법 제4조제7호 단서).

양도 시기 (시행령 제2조제1호): 증권시장 거래는 양도가액이 결제되는 때. 세액은 원 미만 절사.
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
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class SecuritiesTransactionTaxResult(PolicyResult):
    transfer_amount:        str
    market:                 str
    rate_basis:             str
    securities_tax_rate:    str
    rural_special_tax_rate: str
    effective_rate:         str
    securities_tax:         str
    rural_special_tax:      str
    total_tax:              str


@REGISTRY.tool(
    namespace="tax",
    name="kr_securities_transaction",
    description=(
        "한국 주식 양도 시 증권거래세와 농어촌특별세를 계산한다(증권거래세법 제8조, 시행령 제5조 탄력세율, 농특세법 제5조). "
        "transfer_amount 는 양도가액(원), market 은 kospi, kosdaq, konex, k_otc(금융투자협회 장외), "
        "other(그 밖의 장외·비상장, 기본세율 0.35%). year 는 결제일 연도이며 2023~2026 을 지원한다. "
        "세액은 원 미만 절사. 2026 코스피는 0.05%와 농특세 0.15%로 실효 0.20%. "
        "대체거래소 거래와 비과세 양도는 반영하지 않는다. 체결일 연도로 year 를 넣는 것은 오용이다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_securities_transaction(
    transfer_amount: str,
    market:          str,
    year:            int,
) -> SecuritiesTransactionTaxResult:
    """Calculate securities transaction tax and the attached rural special tax.

    Args:
        transfer_amount: 양도가액(원). 0 이상.
        market:          kospi / kosdaq / konex / k_otc / other.
        year:            양도 시기(증권시장 거래는 결제일)가 속하는 연도.

    Returns:
        {transfer_amount, market, rate_basis, securities_tax_rate, rural_special_tax_rate,
         effective_rate, securities_tax, rural_special_tax, total_tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_securities_transaction",
        formula=(
            "증권거래세 = floor(양도가액 × 시장별 세율); "
            "농어촌특별세 = floor(양도가액 × 0.15%) (유가증권시장만); "
            "합계 = 증권거래세 + 농어촌특별세"
        ),
    )

    amount = D(transfer_amount)
    if amount < Decimal("0"):
        raise InvalidInputError("transfer_amount는 0 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_securities_transaction", year)
    data       = policy_doc["data"]
    markets: dict[str, Any] = data["markets"]
    if market not in markets:
        raise InvalidInputError(f"market은 {sorted(markets.keys())} 중 하나여야 합니다.")

    trace.input("transfer_amount", transfer_amount)
    trace.input("market",          market)
    trace.input("year",            year)

    cfg        = markets[market]
    stt_rate   = D(str(cfg["securities_tax_rate"]))
    rural_rate = D(str(cfg["rural_special_tax_rate"]))
    rate_basis = str(cfg["rate_basis"])

    securities_tax = round_apply(amount * stt_rate, 0, RoundingPolicy.DOWN)
    rural_tax      = round_apply(amount * rural_rate, 0, RoundingPolicy.DOWN)
    total_tax      = securities_tax + rural_tax

    trace.step("rate_basis",             rate_basis)
    trace.step("securities_tax_rate",    str(stt_rate))
    trace.step("rural_special_tax_rate", str(rural_rate))
    trace.step("securities_tax",         str(securities_tax))
    trace.step("rural_special_tax",      str(rural_tax))
    trace.output(str(total_tax))

    resp: dict[str, Any] = {
        "transfer_amount":        str(amount),
        "market":                 market,
        "rate_basis":             rate_basis,
        "securities_tax_rate":    str(stt_rate),
        "rural_special_tax_rate": str(rural_rate),
        "effective_rate":         str(stt_rate + rural_rate),
        "securities_tax":         str(securities_tax),
        "rural_special_tax":      str(rural_tax),
        "total_tax":              str(total_tax),
        "policy_version":         policy_doc["policy_version"],
        "trace":                  trace.to_dict(),
    }
    return cast(SecuritiesTransactionTaxResult, enrich_response(resp, policy_doc))
