"""Korean gift tax (증여세) calculator.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03

상속세 및 증여세법 계산 순서:
  1. 증여재산공제(제53조): 관계별 한도에서 증여 전 10년 이내 같은 그룹 기공제액을 뺀 잔여 한도
  2. 혼인·출산 증여재산공제(제53조의2): 직계존속 증여, 평생 1억 한도에서 기공제액을 뺀 잔여
  3. 증여세산출세액(제56조, 제26조 세율)
  4. 세대생략 할증(제57조): 자녀가 아닌 직계비속 수증 시 30%, 미성년자이면서 20억 초과 40%
  5. 신고세액공제(제69조제2항): (산출세액 + 할증액) x 3%
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

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

_ALLOWED_RELATIONSHIPS = frozenset([
    "spouse",
    "lineal_ascendant",
    "lineal_ascendant_minor",
    "lineal_descendant",
    "other_relative",
    "other",
])

_ASCENDANT_RELATIONSHIPS = frozenset(["lineal_ascendant", "lineal_ascendant_minor"])


class TaxKrGiftResult(PolicyResult):
    gift_amount:               str
    deduction:                 str
    marriage_birth_deduction:  str
    total_deduction:           str
    taxable_base:              str
    computed_tax:              str
    generation_skip_surcharge: str
    tax:                       str
    filing_credit:             str
    tax_after_filing_credit:   str
    effective_rate:            str
    marginal_rate:             str
    breakdown:                 list[BracketBreakdown]


def _non_negative(name: str, value: str) -> Decimal:
    """금액 입력을 Decimal 로 바꾸고 음수를 거부한다."""
    amount = D(value)
    if amount < Decimal("0"):
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


@REGISTRY.tool(
    namespace="tax",
    name="kr_gift",
    description=(
        "한국 증여세를 계산한다(상속세및증여세법 제53조·제53조의2·제56조·제57조·제69조). 금액은 원 단위 Decimal 문자열이다. "
        "관계별 증여재산공제에서 10년 내 기공제액을 빼고, marriage_birth_gift=true 이면 직계존속 증여에 혼인·출산 공제 1억을 더하며, "
        "10~50% 누진세율에 generation_skip=true 일 때 세대생략 할증(30%, 미성년 20억 초과 40%)과 기한 내 신고세액공제 3%를 반영한다. "
        "tax 는 신고세액공제 전 금액이고 공제 후는 tax_after_filing_credit 이다. 10년 내 기공제액은 prior_deduction_used_10y 로 직접 넣는다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_gift(
    gift_amount:                    str,
    relationship:                   str,
    year:                           int,
    rounding:                       str  = "HALF_UP",
    decimals:                       int  = 0,
    prior_deduction_used_10y:       str  = "0",
    marriage_birth_gift:            bool = False,
    prior_marriage_birth_deduction: str  = "0",
    generation_skip:                bool = False,
    timely_filing:                  bool = True,
) -> TaxKrGiftResult:
    """Calculate Korean gift tax.

    Args:
        gift_amount:                    증여재산가액 (원)
        relationship:                   증여자와의 관계 (spouse | lineal_ascendant |
                                        lineal_ascendant_minor | lineal_descendant |
                                        other_relative | other).
                                        lineal_ascendant_minor 는 미성년 수증자의 직계존속 증여.
        year:                           과세연도
        rounding:                       반올림 정책
        decimals:                       소수점 자리수
        prior_deduction_used_10y:       증여 전 10년 이내 같은 관계 그룹에서 이미 공제받은 제53조 공제액 (원)
        marriage_birth_gift:            직계존속으로부터 혼인일 전후 2년 또는 자녀 출생·입양일부터
                                        2년 이내 받은 증여인지 여부 (제53조의2)
        prior_marriage_birth_deduction: 이미 공제받은 제53조의2 공제액 합계 (원)
        generation_skip:                수증자가 증여자의 자녀가 아닌 직계비속인지 여부 (제57조).
                                        최근친 직계비속 사망으로 그 직계비속이 받는 경우는 False.
        timely_filing:                  제68조 기한 내 신고 여부. True 면 신고세액공제 적용.

    Returns:
        {gift_amount, deduction, marriage_birth_deduction, total_deduction,
         taxable_base, computed_tax, generation_skip_surcharge, tax,
         filing_credit, tax_after_filing_credit, policy_version, trace}
        tax 는 산출세액에 제57조 할증액을 더한 금액이다.
        제53조 공제와 제53조의2 공제는 제53조 공제를 먼저 적용한다.
    """
    trace = CalcTrace(
        tool="tax.kr_gift",
        formula=(
            "deduction = min(관계별 한도 - 10년 내 기공제액, gift_amount); "
            "marriage_birth = min(1억 - 기공제액, gift_amount - deduction); "
            "taxable = gift_amount - deduction - marriage_birth; "
            "computed_tax = 누진세율 적용(taxable); "
            "tax = computed_tax + 세대생략 할증; "
            "filing_credit = tax x 3%"
        ),
    )

    if relationship not in _ALLOWED_RELATIONSHIPS:
        raise InvalidInputError(
            f"지원하지 않는 relationship: '{relationship}'. "
            f"허용값: {sorted(_ALLOWED_RELATIONSHIPS)}"
        )
    if marriage_birth_gift and relationship not in _ASCENDANT_RELATIONSHIPS:
        raise InvalidInputError(
            "marriage_birth_gift는 직계존속 증여(lineal_ascendant, lineal_ascendant_minor)에만 적용됩니다."
        )
    if generation_skip and relationship not in _ASCENDANT_RELATIONSHIPS:
        raise InvalidInputError(
            "generation_skip은 증여자가 수증자의 직계존속인 경우(lineal_ascendant, lineal_ascendant_minor)에만 적용됩니다."
        )

    policy_enum = _parse_rounding(rounding)
    amount      = _non_negative("gift_amount", gift_amount)
    prior_used  = _non_negative("prior_deduction_used_10y", prior_deduction_used_10y)
    prior_mb    = _non_negative("prior_marriage_birth_deduction", prior_marriage_birth_deduction)

    policy_doc = policy_load("tax", "kr_gift", year)
    data       = policy_doc["data"]
    brackets   = data["brackets"]
    ded_table  = data["relationship_deduction"]
    pv         = policy_doc["policy_version"]

    trace.input("gift_amount",                    gift_amount)
    trace.input("relationship",                   relationship)
    trace.input("year",                           year)
    trace.input("prior_deduction_used_10y",       prior_deduction_used_10y)
    trace.input("marriage_birth_gift",            marriage_birth_gift)
    trace.input("prior_marriage_birth_deduction", prior_marriage_birth_deduction)
    trace.input("generation_skip",                generation_skip)
    trace.input("timely_filing",                  timely_filing)

    limit     = D(str(ded_table[relationship]))
    remaining = limit - prior_used if limit > prior_used else Decimal("0")
    deduction = min(remaining, amount)

    mb_deduction = Decimal("0")
    if marriage_birth_gift:
        mb_limit     = D(str(data["marriage_birth_deduction"]))
        mb_remaining = mb_limit - prior_mb if mb_limit > prior_mb else Decimal("0")
        mb_deduction = min(mb_remaining, amount - deduction)

    total_deduction = deduction + mb_deduction
    taxable         = amount - total_deduction

    computed_tax, eff_rate, marginal_rate, breakdown = _calc_progressive(
        taxable, brackets, policy_enum, decimals
    )

    surcharge      = Decimal("0")
    surcharge_rate = Decimal("0")
    if generation_skip:
        skip_cfg       = data["generation_skip_surcharge"]
        large_minor    = (
            relationship == "lineal_ascendant_minor"
            and amount > D(str(skip_cfg["minor_large_gift_threshold"]))
        )
        surcharge_rate = D(str(skip_cfg["minor_large_gift_rate"] if large_minor else skip_cfg["rate"]))
        surcharge      = round_apply(computed_tax * surcharge_rate, decimals, policy_enum)

    tax_total     = computed_tax + surcharge
    filing_credit = (
        round_apply(tax_total * D(str(data["filing_credit_rate"])), decimals, policy_enum)
        if timely_filing else Decimal("0")
    )
    tax_after_credit = tax_total - filing_credit

    trace.step("deduction",                 str(deduction))
    trace.step("marriage_birth_deduction",  str(mb_deduction))
    trace.step("taxable_base",              str(taxable))
    trace.step("breakdown",                 breakdown)
    trace.step("computed_tax",              str(computed_tax))
    trace.step("generation_skip_rate",      str(surcharge_rate))
    trace.step("generation_skip_surcharge", str(surcharge))
    trace.step("filing_credit",             str(filing_credit))
    trace.output(str(tax_total))

    resp: dict[str, Any] = {
        "gift_amount":               str(amount),
        "deduction":                 str(deduction),
        "marriage_birth_deduction":  str(mb_deduction),
        "total_deduction":           str(total_deduction),
        "taxable_base":              str(taxable),
        "computed_tax":              str(computed_tax),
        "generation_skip_surcharge": str(surcharge),
        "tax":                       str(tax_total),
        "filing_credit":             str(filing_credit),
        "tax_after_filing_credit":   str(tax_after_credit),
        "effective_rate":            str(eff_rate),
        "marginal_rate":             str(marginal_rate),
        "breakdown":                 breakdown,
        "policy_version":            pv,
        "trace":                     trace.to_dict(),
    }
    return cast(TaxKrGiftResult, enrich_response(resp, policy_doc))
