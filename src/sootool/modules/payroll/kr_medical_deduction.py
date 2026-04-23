"""Korean medical expense tax credit (의료비 세액공제) calculator.

Author: 최진호
Date: 2026-04-24

소득세법 제59조의4 제2항 의료비 세액공제:
  - 공제 대상액 = max(0, 지출 의료비 - 총급여의 3%)
  - 일반 의료비: 15% 세액공제, 연 700만원 한도
  - 본인·장애인·65세 이상·6세 이하: 15%, 한도 없음
  - 난임시술비: 30%, 한도 없음
  - 미숙아·선천성이상아: 20%, 한도 없음

입력은 범주별 의료비 지출액(원)을 문자열로 받는다.
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
    namespace="payroll",
    name="kr_medical_deduction",
    description=(
        "한국 의료비 세액공제(소득세법 §59의4) 계산. "
        "총급여 3% 초과분에 대해 일반 15%·난임 30%·미숙아 20% 공제."
    ),
    version="1.0.0",
)
def payroll_kr_medical_deduction(
    gross_income:     str,
    general_medical:  str,
    year:             int,
    special_medical:  str = "0",
    infertility:      str = "0",
    premature:        str = "0",
) -> dict[str, Any]:
    """Calculate medical expense tax credit.

    Args:
        gross_income:     총급여(원).
        general_medical:  일반 의료비 지출액(원). 본인·장애인 등 특수대상 제외.
        year:             과세연도.
        special_medical:  본인·장애인·65세 이상·6세 이하 의료비(한도 없음).
        infertility:      난임시술비(원).
        premature:        미숙아·선천성이상아 의료비(원).

    Returns:
        {gross_income, threshold, total_expense, deductible_expense,
         general_credit, special_credit, infertility_credit, premature_credit,
         total_credit, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_medical_deduction",
        formula=(
            "threshold = 총급여 × 3%; "
            "deductible = max(0, (일반+특수+난임+미숙아) - threshold); "
            "각 범주별 공제는 해당 지출액에서 threshold를 일반→특수→난임→미숙아 순 차감 후 "
            "rate × (한도 적용)로 계산"
        ),
    )

    g   = D(gross_income)
    gen = D(general_medical)
    spe = D(special_medical)
    inf = D(infertility)
    pre = D(premature)

    for name, val in [
        ("gross_income",    g),
        ("general_medical", gen),
        ("special_medical", spe),
        ("infertility",     inf),
        ("premature",       pre),
    ]:
        if val < Decimal("0"):
            raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")

    policy_doc = policy_load("payroll", "kr_yearend_deductions", year)
    data       = policy_doc["data"]["medical"]
    pv         = policy_doc["policy_version"]

    floor_rate  = D(str(data["gross_income_floor_rate"]))
    credit_rate = D(str(data["credit_rate"]))
    inf_rate    = D(str(data["infertility_rate"]))
    pre_rate    = D(str(data["premature_rate"]))
    gen_limit   = D(str(data["general_limit"]))

    trace.input("gross_income",    gross_income)
    trace.input("general_medical", general_medical)
    trace.input("special_medical", special_medical)
    trace.input("infertility",     infertility)
    trace.input("premature",       premature)
    trace.input("year",            year)

    threshold      = round_apply(g * floor_rate, 0, RoundingPolicy.HALF_UP)
    total_expense  = gen + spe + inf + pre
    deductible     = total_expense - threshold
    if deductible < Decimal("0"):
        deductible = Decimal("0")

    # threshold를 범주 우선순위 (일반 → 특수 → 난임 → 미숙아) 순으로 차감
    remaining = threshold
    # 일반: 먼저 threshold와 한도 적용
    gen_after_thr = gen - min(gen, remaining)
    remaining     = remaining - min(gen, remaining)
    gen_after_lim = gen_after_thr if gen_after_thr <= gen_limit else gen_limit

    spe_after_thr = spe - min(spe, remaining)
    remaining     = remaining - min(spe, remaining)

    inf_after_thr = inf - min(inf, remaining)
    remaining     = remaining - min(inf, remaining)

    pre_after_thr = pre - min(pre, remaining)
    # remaining은 마지막 이후 사용 안 함

    general_credit    = round_apply(gen_after_lim * credit_rate, 0, RoundingPolicy.DOWN)
    special_credit    = round_apply(spe_after_thr * credit_rate, 0, RoundingPolicy.DOWN)
    infertility_credit = round_apply(inf_after_thr * inf_rate,   0, RoundingPolicy.DOWN)
    premature_credit   = round_apply(pre_after_thr * pre_rate,   0, RoundingPolicy.DOWN)

    total_credit = (
        general_credit + special_credit + infertility_credit + premature_credit
    )

    trace.step("threshold",          str(threshold))
    trace.step("total_expense",      str(total_expense))
    trace.step("deductible_expense", str(deductible))
    trace.step("general_credit",     str(general_credit))
    trace.step("special_credit",     str(special_credit))
    trace.step("infertility_credit", str(infertility_credit))
    trace.step("premature_credit",   str(premature_credit))
    trace.output(str(total_credit))

    resp: dict[str, Any] = {
        "gross_income":        str(g),
        "threshold":           str(threshold),
        "total_expense":       str(total_expense),
        "deductible_expense":  str(deductible),
        "general_credit":      str(general_credit),
        "special_credit":      str(special_credit),
        "infertility_credit":  str(infertility_credit),
        "premature_credit":    str(premature_credit),
        "total_credit":        str(total_credit),
        "policy_version":      pv,
        "trace":               trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
