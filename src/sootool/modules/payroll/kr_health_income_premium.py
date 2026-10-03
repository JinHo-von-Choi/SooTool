"""Korean health insurance non-salary income premium and annual premium settlement calculator.

작성자: 최진호
작성일: 2026-10-03

보수 외 소득월액보험료 (국민건강보험법 제69조제4항제2호, 제71조제1항, 제76조제2항):
  1. 연간 보수 외 소득 X = 이자 + 배당 + 사업 + 근로 + 연금 + 기타소득
     (이자·배당 합계가 1천만원 이하이면 합산하지 않는다. 시행규칙 제44조제1항 단서)
  2. X 가 연 2천만원 이하이면 부과하지 않는다 (시행령 제41조제4항)
  3. 보수 외 소득월액 = (X - 2천만원) / 12 x sum(소득 종류별 비율 x 평가율)
     (이자·배당·사업·기타 100%, 근로·연금 50%. 시행규칙 제44조제2항)
  4. 보험료 = min(보수 외 소득월액 x 보험료율, 월 상한), 직장가입자 전액 부담
  5. 장기요양보험료 = 보험료 x (장기요양보험료율 / 건강보험료율) (노인장기요양보험법 제9조제1항)

보수월액보험료 정산 (시행령 제34조제1항, 제36조제1항, 제39조):
  보수월액 = 보수총액 / 근무 개월수. 근무한 달마다 그 달의 보험료율, 장기요양 비율, 보험료
  상·하한으로 근로자 부담 보험료를 다시 산정해 합하고, 이미 낸 보험료와의 차액을 추가징수(양수)
  또는 반환(음수)한다. 추가징수금액의 분할납부 가능 여부는 시행령 제39조제4항으로 판정한다.
  2026-10-01 전 규정의 기준(고지하는 달의 근로자 부담 보수월액보험료)은 다시 산정한 마지막 달의
  근로자 부담 보험료로 갈음한다.

보험료율, 장기요양 비율, 보수월액보험료 상·하한은 payroll/kr_4insurance 정책에서 읽는다.
근로자 보수월액 보험료와 장기요양은 10원 미만을 버리고 소득월액보험료는 원 미만을 버린다. 소득 자료 연도(1~10월분 전전년도, 11·12월분 전년도) 선택,
소득월액 조정 신청, 공무원·사립학교 교원 분담 비율, 휴직자 특례는 모델링하지 않는다.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, NotRequired, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.policy_context import POLICY_INCLUDE_PROPOSED, policy_context
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.payroll.kr_salary import _truncate_premium
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO   = Decimal("0")
_TWELVE = Decimal("12")

_INCOME_KINDS = ("interest", "dividend", "business", "wage", "pension", "other")


class IncomePremium(TypedDict):
    """보수 외 소득월액보험료 산정 결과."""

    annual_non_salary_income:  str
    financial_income_included: bool
    threshold_annual:          str
    subject:                   bool
    evaluation_factor:         str
    income_monthly:            str
    premium_rate:              str
    health_premium:            str
    premium_capped:            bool
    long_term_care_premium:    str
    total:                     str


class SettlementMonth(TypedDict):
    month:                  int
    health_premium:         str
    long_term_care_premium: str


class Settlement(TypedDict):
    """보수월액보험료 연간 정산 결과 (근로자 부담분)."""

    remuneration_total:             str
    months_worked:                  int
    remuneration_monthly:           str
    recalculated_health_premium:    str
    recalculated_long_term_care:    str
    health_premium_paid:            str
    long_term_care_paid:            str
    health_difference:              str
    long_term_care_difference:      str
    total_difference:               str
    installment_eligible:           bool
    installment_threshold:          str
    installment_basis:              str
    max_installments:               int
    months:                         list[SettlementMonth]


class KrHealthIncomePremiumResult(PolicyResult):
    income_premium: IncomePremium
    settlement:     NotRequired[Settlement]


def _floor_won(value: Decimal) -> Decimal:
    return round_apply(value, 0, RoundingPolicy.DOWN)


def _non_negative(name: str, value: str) -> Decimal:
    amount = D(value)
    if amount < _ZERO:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


def _employee_salary_premium(remuneration_monthly: Decimal, hi_cfg: dict[str, Any]) -> tuple[Decimal, Decimal]:
    """근로자 부담 보수월액보험료와 장기요양보험료. 월별 보험료 상·하한의 근로자 부담분으로 제한한다."""
    employee_rate = D(str(hi_cfg["employee_rate"]))
    share         = employee_rate / (employee_rate + D(str(hi_cfg["employer_rate"])))
    unit          = D(str(hi_cfg.get("premium_truncation_unit", 1)))
    health        = _truncate_premium(remuneration_monthly * employee_rate, unit)
    if hi_cfg.get("premium_min_monthly_total") is not None:
        health = max(health, _truncate_premium(D(str(hi_cfg["premium_min_monthly_total"])) * share, unit))
    if hi_cfg.get("premium_max_monthly_total") is not None:
        health = min(health, _truncate_premium(D(str(hi_cfg["premium_max_monthly_total"])) * share, unit))
    ltc = _truncate_premium(health * D(str(hi_cfg["long_term_care_rate_of_health"])), unit)
    return health, ltc


@REGISTRY.tool(
    namespace="payroll",
    name="kr_health_income_premium",
    description=(
        "건강보험 직장가입자의 보수 외 소득월액보험료(국민건강보험법 제71조: 연 2천만원 초과분의 1/12, 근로·연금소득 50% 평가, "
        "이자·배당 1천만원 이하 제외, 월 상한 4,591,740원)와 장기요양보험료, 보수총액 기준 보수월액보험료 연간 정산 차액과 "
        "분할납부 가능 여부를 계산한다. 소득은 소득 종류별 연간 소득금액(원 문자열), year 는 부과 또는 보수 귀속 연도, "
        "원 미만 버림. 지역가입자 보험료 계산에 쓰면 오용이다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_health_income_premium(
    year:                      int,
    interest_income:           str        = "0",
    dividend_income:           str        = "0",
    business_income:           str        = "0",
    wage_income:               str        = "0",
    pension_income:            str        = "0",
    other_income:              str        = "0",
    annual_remuneration_total: str | None = None,
    start_month:               int        = 1,
    end_month:                 int        = 12,
    health_premium_paid:       str | None = None,
    ltc_premium_paid:          str | None = None,
) -> KrHealthIncomePremiumResult:
    """Calculate the non-salary income premium and the annual salary premium settlement.

    Args:
        year:                      보험료 부과 연도이자 정산 대상 보수 귀속 연도
        interest_income:           연간 이자소득금액(원)
        dividend_income:           연간 배당소득금액(원)
        business_income:           연간 사업소득금액(원)
        wage_income:               보수월액에 포함되지 않은 연간 근로소득(총급여, 원)
        pension_income:            연간 연금소득(총연금액, 공적연금 포함, 원)
        other_income:              연간 기타소득금액(원)
        annual_remuneration_total: 정산 대상 연도 보수총액(원). 지정하면 정산을 계산한다
        start_month:               정산 대상 근무 시작 월(1~12)
        end_month:                 정산 대상 근무 종료 월(1~12)
        health_premium_paid:       이미 낸 근로자 부담 건강보험료 합계(원). 정산 시 필수
        ltc_premium_paid:          이미 낸 근로자 부담 장기요양보험료 합계(원). 정산 시 필수

    Returns:
        {income_premium, settlement?, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_health_income_premium",
        formula=(
            "X = 보수 외 소득 합계(이자·배당 1천만원 이하 제외); "
            "소득월액 = X > 2천만원 ? (X - 2천만원) / 12 x sum(비율 x 평가율) : 0; "
            "보험료 = min(소득월액 x 보험료율, 상한), 장기요양 = 보험료 x 비율; "
            "정산 = sum(월별 재산정 근로자 보험료) - 기납부 보험료"
        ),
    )

    incomes = {
        kind: _non_negative(f"{kind}_income", value)
        for kind, value in zip(
            _INCOME_KINDS,
            (interest_income, dividend_income, business_income, wage_income, pension_income, other_income),
            strict=True,
        )
    }

    settle = annual_remuneration_total is not None
    if settle:
        if health_premium_paid is None or ltc_premium_paid is None:
            raise InvalidInputError(
                "정산을 계산하려면 health_premium_paid와 ltc_premium_paid를 함께 입력해야 합니다."
            )
        if not 1 <= start_month <= end_month <= 12:
            raise InvalidInputError("start_month와 end_month는 1 이상 12 이하이고 start_month <= end_month여야 합니다.")
        remuneration = _non_negative("annual_remuneration_total", cast(str, annual_remuneration_total))
        paid_health  = _non_negative("health_premium_paid", health_premium_paid)
        paid_ltc     = _non_negative("ltc_premium_paid", ltc_premium_paid)
    elif health_premium_paid is not None or ltc_premium_paid is not None:
        raise InvalidInputError("health_premium_paid와 ltc_premium_paid는 annual_remuneration_total과 함께 입력합니다.")

    # 정산은 근무한 달마다 그 달 1일에 시행 중인 4대보험 정책을 쓴다.
    month_configs: list[tuple[int, dict[str, Any]]] = []
    if settle:
        include_proposed = POLICY_INCLUDE_PROPOSED.get()
        for month in range(start_month, end_month + 1):
            with policy_context(as_of=date(year, month, 1), include_proposed=include_proposed):
                month_doc = policy_load("payroll", "kr_4insurance", year)
            month_configs.append((month, month_doc["data"]["health_insurance"]))

    ins_doc    = policy_load("payroll", "kr_4insurance", year)
    policy_doc = policy_load("payroll", "kr_health_income_premium", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]
    hi_cfg     = ins_doc["data"]["health_insurance"]

    trace.input("year", year)
    for kind in _INCOME_KINDS:
        trace.input(f"{kind}_income", str(incomes[kind]))
    trace.input("annual_remuneration_total", annual_remuneration_total)
    trace.input("start_month",               start_month)
    trace.input("end_month",                 end_month)
    trace.input("health_premium_paid",       health_premium_paid)
    trace.input("ltc_premium_paid",          ltc_premium_paid)

    # --- 보수 외 소득월액보험료 ---
    financial          = incomes["interest"] + incomes["dividend"]
    financial_included = financial > D(str(data["financial_income_exclusion_max"]))
    counted            = {
        kind: amount for kind, amount in incomes.items()
        if financial_included or kind not in ("interest", "dividend")
    }
    annual_total = sum(counted.values(), _ZERO)
    threshold    = D(str(data["non_salary_income_threshold_annual"]))
    subject      = annual_total > threshold

    rates     = data["evaluation_rates"]
    evaluated = sum((amount * D(str(rates[kind])) for kind, amount in counted.items()), _ZERO)
    factor    = evaluated / annual_total if subject else _ZERO
    # (X - 기준) / 12 x (평가 소득 / X) 를 나눗셈 한 번으로 계산해 끝자리 오차를 줄인다.
    income_monthly = (annual_total - threshold) * evaluated / (annual_total * _TWELVE) if subject else _ZERO

    premium_rate   = D(str(hi_cfg["employee_rate"])) + D(str(hi_cfg["employer_rate"]))
    cap            = D(str(data["income_premium_max_monthly"]))
    raw_premium    = income_monthly * premium_rate
    premium_capped = raw_premium > cap
    health_premium = _floor_won(cap if premium_capped else raw_premium)
    ltc_premium    = _floor_won(health_premium * D(str(hi_cfg["long_term_care_rate_of_health"])))

    income_part: IncomePremium = {
        "annual_non_salary_income":  str(annual_total),
        "financial_income_included": financial_included,
        "threshold_annual":          str(threshold),
        "subject":                   subject,
        "evaluation_factor":         str(factor),
        "income_monthly":            str(income_monthly),
        "premium_rate":              str(premium_rate),
        "health_premium":            str(health_premium),
        "premium_capped":            premium_capped,
        "long_term_care_premium":    str(ltc_premium),
        "total":                     str(health_premium + ltc_premium),
    }
    trace.step("income_premium",                 income_part)
    trace.step("insurance_policy_effective_date", ins_doc["policy_version"]["effective_date"])

    resp: dict[str, Any] = {"income_premium": income_part}

    # --- 보수월액보험료 정산 ---
    if settle:
        months_worked        = len(month_configs)
        remuneration_monthly = remuneration / Decimal(months_worked)
        monthly_rows: list[SettlementMonth] = []
        total_health = _ZERO
        total_ltc    = _ZERO
        for month, month_cfg in month_configs:
            health, ltc = _employee_salary_premium(remuneration_monthly, month_cfg)
            total_health += health
            total_ltc    += ltc
            monthly_rows.append({
                "month":                  month,
                "health_premium":         str(health),
                "long_term_care_premium": str(ltc),
            })
        health_diff = total_health - paid_health
        ltc_diff    = total_ltc - paid_ltc

        inst_cfg = data["settlement_installment"]
        basis    = str(inst_cfg["threshold_basis"])
        if basis == "premium_floor":
            inst_threshold = D(str(hi_cfg["premium_min_monthly_total"]))
        elif basis == "monthly_premium":
            inst_threshold = D(monthly_rows[-1]["health_premium"])
        else:
            raise InvalidInputError(f"알 수 없는 분할납부 기준입니다: {basis!r}")
        installment_eligible = health_diff > _ZERO and health_diff >= inst_threshold

        settlement: Settlement = {
            "remuneration_total":          str(remuneration),
            "months_worked":               months_worked,
            "remuneration_monthly":        str(remuneration_monthly),
            "recalculated_health_premium": str(total_health),
            "recalculated_long_term_care": str(total_ltc),
            "health_premium_paid":         str(paid_health),
            "long_term_care_paid":         str(paid_ltc),
            "health_difference":           str(health_diff),
            "long_term_care_difference":   str(ltc_diff),
            "total_difference":            str(health_diff + ltc_diff),
            "installment_eligible":        installment_eligible,
            "installment_threshold":       str(inst_threshold),
            "installment_basis":           basis,
            "max_installments":            int(inst_cfg["max_installments"]),
            "months":                      monthly_rows,
        }
        trace.step("settlement", settlement)
        resp["settlement"] = settlement
        trace.output({"income_premium_total": income_part["total"], "settlement_difference": str(health_diff + ltc_diff)})
    else:
        trace.output({"income_premium_total": income_part["total"]})

    resp["policy_version"] = pv
    resp["trace"]          = trace.to_dict()
    return cast(KrHealthIncomePremiumResult, enrich_response(resp, policy_doc))
