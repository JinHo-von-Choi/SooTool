"""Korean comprehensive income tax (종합소득세 신고 흐름) calculator.

작성자: 최진호
작성일: 2026-10-04

소득세법에 따른 종합소득 합산 과세 흐름을 한 번에 계산한다.

  1. 소득금액
     근로: 총급여액 - 근로소득공제(제47조, kr_withholding 정책)
     사업: 소득금액 또는 총수입금액 - 필요경비
     이자·배당: 원천징수(14%) 합계가 종합과세기준금액(2천만원) 이하이면 분리과세(제14조제3항제6호).
       초과하면 이자, 배당가산 대상이 아닌 배당, 배당가산 대상 배당 순으로 기준금액을 채우고
       (시행령 제116조의2) 기준금액을 넘는 배당가산 대상 배당에 10%를 더한다(제17조제3항, 제56조제4항).
     연금: 총연금액 - 연금소득공제(제47조의2, kr_pension_income 정책)
     기타: 의제필요경비 60% 대상(시행령 제87조제1호의2)과 그 밖의 기타소득금액의 합계가 300만원 이하이면
       분리과세(20%), 합산을 선택하거나 300만원을 넘으면 종합과세(제14조제3항제8호가목)
  2. 종합소득공제: 기본공제 1명당 150만원(제50조), 추가공제(제51조, 인적공제는 종합소득금액 한도),
     그 밖의 소득공제 합계 입력
  3. 산출세액: 기본세율(제55조, kr_income 정책). 금융소득 종합과세 시 제62조 비교과세
       제1호 = 기본세율(과세표준 - 기준금액) + 기준금액 x 14%
       제2호 = 이자소득등 x 14% + 기본세율(다른 종합소득금액 - 종합소득공제)
  4. 세액공제: 배당세액공제 = min(배당가산액, 산출세액 - 제62조제2호 금액)(제15조제2호, 제56조),
     근로소득세액공제(제59조, 근로소득분 산출세액은 시행령 제119조의3제1항 비율),
     자녀세액공제(제59조의2), 표준세액공제(제59조의4제9항), 그 밖의 세액공제 합계 입력
  5. 결정세액 = max(0, 산출세액 - 세액공제 합계), 지방소득세 = 결정세액 x 10%

금액은 원 단위이며 각 세액과 공제액의 원 미만은 버린다. 결손금 통산과 이월결손금, 중간예납·기납부세액,
성실신고확인, 외국납부세액공제, 비영업대금이익(25%)·출자공동사업자 배당·원천징수되지 않은 금융소득,
분리과세 주택임대소득, 특별소득공제와 특별세액공제 항목별 계산은 다루지 않는다.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal, NotRequired, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax._credits import STANDARD_TAX_CREDIT, _labor_income_tax_credit
from sootool.modules.tax.kr_local_income_tax import _LOCAL_RATE
from sootool.modules.tax.kr_pension_income import _pension_income_deduction
from sootool.modules.tax.kr_withholding import _calc_labor_income_deduction
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO = Decimal("0")


class FinancialComparison(TypedDict):
    """금융소득 종합과세 비교과세(소득세법 제62조)의 두 세액."""

    aggregated_method_tax: str
    separate_method_tax:   str
    applied:               Literal["aggregated", "separate"]


class ReferencedPolicy(TypedDict):
    """함께 읽은 정책 문서의 식별 정보."""

    key:            str
    effective_date: str
    sha256:         str


class TaxKrComprehensiveIncomeTaxResult(PolicyResult):
    labor_income_deduction:         str
    labor_income_amount:            str
    business_income_amount:         str
    financial_income_total:         str
    financial_income_aggregated:    bool
    dividend_gross_up:              str
    financial_income_amount:        str
    financial_income_separate_tax:  str
    pension_income_deduction:       str
    pension_income_amount:          str
    other_income_total:             str
    other_income_aggregated:        bool
    other_income_separate_tax:      str
    comprehensive_income:           str
    basic_deduction:                str
    additional_deduction:           str
    personal_deduction:             str
    other_income_deductions:        str
    taxable_income:                 str
    computed_tax:                   str
    financial_comparison:           NotRequired[FinancialComparison]
    dividend_tax_credit:            str
    labor_income_tax_credit:        str
    child_tax_credit:               str
    standard_tax_credit:            str
    other_tax_credits:              str
    total_tax_credits:              str
    decided_tax:                    str
    local_income_tax:               str
    total_tax:                      str
    notes:                          list[str]
    referenced_policies:            list[ReferencedPolicy]


def _amount(name: str, value: str) -> Decimal:
    """금액 입력을 Decimal 로 바꾸고 음수를 거부한다."""
    amount = D(value)
    if amount < _ZERO:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


def _count(name: str, value: int) -> int:
    if value < 0:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return value


def _floor_won(value: Decimal) -> Decimal:
    return round_apply(value, 0, RoundingPolicy.DOWN)


def _basic_rate_tax(base: Decimal, brackets: list[dict[str, Any]]) -> Decimal:
    """기본세율(소득세법 제55조제1항) 세액, 원 미만 버림. 과세표준이 0 이하이면 0."""
    if base <= _ZERO:
        return _ZERO
    tax, _eff, _marg, _breakdown = _calc_progressive(base, brackets, RoundingPolicy.DOWN, 0)
    return tax


def _business_income(
    business_income:   str | None,
    business_revenue:  str,
    business_expenses: str,
) -> Decimal:
    """사업소득금액. 소득금액 직접 입력과 총수입금액·필요경비 입력 중 하나만 받는다."""
    revenue  = _amount("business_revenue", business_revenue)
    expenses = _amount("business_expenses", business_expenses)
    if business_income is not None:
        if revenue > _ZERO or expenses > _ZERO:
            raise InvalidInputError(
                "business_income과 business_revenue·business_expenses는 함께 입력할 수 없습니다."
            )
        return _amount("business_income", business_income)
    if expenses > revenue:
        raise InvalidInputError(
            "business_expenses가 business_revenue를 넘습니다. 결손금 통산은 계산하지 않습니다."
        )
    return revenue - expenses


def _child_tax_credit(children: int, birth_orders: list[int], rule: Mapping[str, Any]) -> Decimal:
    """자녀세액공제 (소득세법 제59조의2제1항·제3항)."""
    if children == 0:
        credit = _ZERO
    elif children == 1:
        credit = D(str(rule["one"]))
    else:
        credit = D(str(rule["two"])) + D(str(rule["per_child_over_two"])) * Decimal(children - 2)
    for order in birth_orders:
        if order == 1:
            credit += D(str(rule["birth_first"]))
        elif order == 2:
            credit += D(str(rule["birth_second"]))
        else:
            credit += D(str(rule["birth_third_or_later"]))
    return credit


def _referenced(key: str, doc: Mapping[str, Any]) -> ReferencedPolicy:
    pv = doc["policy_version"]
    return {"key": key, "effective_date": str(pv["effective_date"]), "sha256": str(pv["sha256"])}


@REGISTRY.tool(
    namespace="tax",
    name="kr_comprehensive_income_tax",
    description=(
        "종합소득세 신고 흐름(소득금액 합산, 종합소득공제, 과세표준, 산출세액, 세액공제, 결정세액, 지방소득세 10%)을 계산한다. "
        "금액은 원 단위 Decimal 문자열, year 필수, 원 미만 버림. 근로(총급여), 사업, 이자·배당(2천만원 초과 시 배당가산 10%, "
        "제62조 비교과세, 배당세액공제), 연금(총연금액), 기타소득(60% 의제경비, 300만원 이하 분리과세)을 받는다. "
        "결손금 통산, 중간예납·기납부세액, 외국납부세액공제는 계산하지 않고 특별공제는 합계로 넣는다. "
        "근로소득만 있는 연말정산에는 payroll.kr_year_end_tax_settlement 를 쓴다."
    ),
    version="1.0.0",
    policy=True,
)
def tax_kr_comprehensive_income_tax(
    year:                          int,
    total_salary:                  str            = "0",
    business_income:               str | None     = None,
    business_revenue:              str            = "0",
    business_expenses:             str            = "0",
    interest_income:               str            = "0",
    dividend_gross_up_eligible:    str            = "0",
    dividend_other:                str            = "0",
    pension_gross:                 str            = "0",
    other_income_deemed_revenue:   str            = "0",
    other_income_actual_expenses:  str            = "0",
    other_income_amount:           str            = "0",
    other_income_aggregate:        bool           = False,
    dependents:                    int            = 1,
    elderly_count:                 int            = 0,
    disabled_count:                int            = 0,
    woman_deduction:               bool           = False,
    single_parent:                 bool           = False,
    other_income_deductions:       str            = "0",
    children_count:                int            = 0,
    newborn_birth_orders:          list[int] | None = None,
    other_tax_credits:             str            = "0",
    apply_standard_tax_credit:     bool           = False,
    diligent_business_operator:    bool           = False,
) -> TaxKrComprehensiveIncomeTaxResult:
    """Calculate Korean comprehensive income tax from income by type.

    Args:
        year:                         귀속 과세연도.
        total_salary:                 근로소득 총급여액(원, 비과세 제외).
        business_income:              사업소득금액(원). 주면 business_revenue·business_expenses 는 0이어야 한다.
        business_revenue:             사업소득 총수입금액(원).
        business_expenses:            사업소득 필요경비(원). 총수입금액을 넘을 수 없다.
        interest_income:              원천징수세율 14%가 적용된 이자소득 총수입금액(원).
        dividend_gross_up_eligible:   배당가산(소득세법 제17조제3항 단서) 대상 배당 총수입금액(원), 14% 원천징수분.
        dividend_other:               배당가산 대상이 아닌 배당 총수입금액(원), 14% 원천징수분.
        pension_gross:                종합과세할 총연금액(원). 공적연금과 분리과세하지 않는 사적연금.
        other_income_deemed_revenue:  시행령 제87조제1호의2 대상 기타소득 총수입금액(원). 필요경비 60% 의제.
        other_income_actual_expenses: 위 기타소득의 실제 필요경비(원). 60%보다 크면 이 금액을 쓴다.
        other_income_amount:          그 밖의 기타소득금액(원, 필요경비 차감 후, 제14조제3항제8호가목 대상).
        other_income_aggregate:       기타소득금액 300만원 이하일 때 분리과세 대신 합산을 선택하는지.
        dependents:                   기본공제 대상 인원(본인 포함, 1 이상).
        elderly_count:                기본공제 대상자 중 70세 이상 인원.
        disabled_count:               기본공제 대상자 중 장애인 인원.
        woman_deduction:              부녀자공제 요건(배우자 없는 여성 세대주로 부양가족 있음 또는 배우자 있는 여성) 충족.
                                      종합소득금액 3천만원 초과이면 적용하지 않는다.
        single_parent:                한부모공제 요건(배우자 없이 기본공제 대상 직계비속·입양자 있음) 충족.
        other_income_deductions:      그 밖의 종합소득공제 합계(원): 연금보험료공제, 특별소득공제, 조세특례제한법 소득공제.
        children_count:               자녀세액공제 대상 자녀·손자녀 수(해당 연도 연령기준 충족, 기본공제 대상자).
        newborn_birth_orders:         해당 연도 출산·입양 신고 자녀의 출생 순위 목록(예: [2]).
        other_tax_credits:            그 밖의 세액공제 합계(원): 특별세액공제, 연금계좌세액공제, 기장세액공제 등.
        apply_standard_tax_credit:    표준세액공제 적용 여부. 근로소득자는 특별소득공제·특별세액공제·월세세액공제를
                                      신청하지 않은 경우에만 해당한다.
        diligent_business_operator:   근로소득이 없는 성실사업자(표준세액공제 12만원)인지.

    Returns:
        TaxKrComprehensiveIncomeTaxResult. 소득 종류별 금액, 공제, 산출세액, 세액공제, 결정세액, 지방소득세.
    """
    trace = CalcTrace(
        tool="tax.kr_comprehensive_income_tax",
        formula=(
            "종합소득금액 = 근로 + 사업 + 금융(2천만원 초과 시, 배당가산 포함) + 연금 + 기타(종합과세분); "
            "과세표준 = 종합소득금액 - 인적공제(종합소득금액 한도) - 그 밖의 소득공제; "
            "산출세액 = 기본세율 또는 max(기본세율(과세표준 - 2천만원) + 2천만원 x 14%, "
            "금융소득 x 14% + 기본세율(다른 소득금액 - 공제)); "
            "결정세액 = max(0, 산출세액 - 배당·근로·자녀·표준·그 밖의 세액공제); 지방소득세 = 결정세액 x 10%"
        ),
    )

    salary         = _amount("total_salary", total_salary)
    business       = _business_income(business_income, business_revenue, business_expenses)
    interest       = _amount("interest_income", interest_income)
    div_eligible   = _amount("dividend_gross_up_eligible", dividend_gross_up_eligible)
    div_other      = _amount("dividend_other", dividend_other)
    pension        = _amount("pension_gross", pension_gross)
    deemed_revenue = _amount("other_income_deemed_revenue", other_income_deemed_revenue)
    actual_expense = _amount("other_income_actual_expenses", other_income_actual_expenses)
    other_net      = _amount("other_income_amount", other_income_amount)
    extra_ded      = _amount("other_income_deductions", other_income_deductions)
    extra_credit   = _amount("other_tax_credits", other_tax_credits)
    birth_orders   = list(newborn_birth_orders or [])

    if actual_expense > deemed_revenue:
        raise InvalidInputError(
            "other_income_actual_expenses가 other_income_deemed_revenue를 넘습니다. 기타소득 결손은 계산하지 않습니다."
        )
    if dependents < 1:
        raise InvalidInputError("dependents는 1 이상이어야 합니다 (본인 포함).")
    for name, value in (("elderly_count", elderly_count), ("disabled_count", disabled_count)):
        if _count(name, value) > dependents:
            raise InvalidInputError(f"{name}는 dependents를 넘을 수 없습니다.")
    _count("children_count", children_count)
    if any(order < 1 for order in birth_orders):
        raise InvalidInputError("newborn_birth_orders의 출생 순위는 1 이상이어야 합니다.")
    if children_count + len(birth_orders) > dependents - 1:
        raise InvalidInputError(
            "children_count와 newborn_birth_orders 인원의 합은 본인을 제외한 기본공제 대상 인원(dependents - 1)을 넘을 수 없습니다."
        )

    doc      = policy_load("tax", "kr_comprehensive_income", year)
    inc_doc  = policy_load("tax", "kr_income", year)
    wh_doc   = policy_load("tax", "kr_withholding", year)
    pen_doc  = policy_load("tax", "kr_pension_income", year)
    data     = doc["data"]
    wh_data  = wh_doc["data"]
    brackets = inc_doc["data"]["brackets"]

    trace.input("year",                         year)
    trace.input("total_salary",                 total_salary)
    trace.input("business_income",              business_income)
    trace.input("business_revenue",             business_revenue)
    trace.input("business_expenses",            business_expenses)
    trace.input("interest_income",              interest_income)
    trace.input("dividend_gross_up_eligible",   dividend_gross_up_eligible)
    trace.input("dividend_other",               dividend_other)
    trace.input("pension_gross",                pension_gross)
    trace.input("other_income_deemed_revenue",  other_income_deemed_revenue)
    trace.input("other_income_actual_expenses", other_income_actual_expenses)
    trace.input("other_income_amount",          other_income_amount)
    trace.input("other_income_aggregate",       other_income_aggregate)
    trace.input("dependents",                   dependents)
    trace.input("elderly_count",                elderly_count)
    trace.input("disabled_count",               disabled_count)
    trace.input("woman_deduction",              woman_deduction)
    trace.input("single_parent",                single_parent)
    trace.input("other_income_deductions",      other_income_deductions)
    trace.input("children_count",               children_count)
    trace.input("newborn_birth_orders",         birth_orders)
    trace.input("other_tax_credits",            other_tax_credits)
    trace.input("apply_standard_tax_credit",    apply_standard_tax_credit)
    trace.input("diligent_business_operator",   diligent_business_operator)

    notes: list[str] = []

    # 1. 근로소득금액 (제20조제2항, 제47조)
    labor_cap    = wh_data.get("labor_income_deduction_cap")
    labor_ded    = _floor_won(_calc_labor_income_deduction(
        salary, wh_data["labor_income_deduction_brackets"], None if labor_cap is None else D(str(labor_cap)),
    ))
    labor_income = salary - labor_ded

    # 2. 금융소득 (제14조제3항제6호, 제17조제3항, 시행령 제116조의2)
    threshold    = D(str(data["financial_income_threshold"]))
    fin_rate     = D(str(data["financial_withholding_rate"]))
    fin_total    = interest + div_eligible + div_other
    fin_aggr     = fin_total > threshold
    if fin_aggr:
        gross_up_base = min(div_eligible, fin_total - threshold)
        gross_up      = _floor_won(gross_up_base * D(str(data["dividend_gross_up_rate"])))
        fin_amount    = fin_total + gross_up
        fin_sep_tax   = _ZERO
    else:
        gross_up    = _ZERO
        fin_amount  = _ZERO
        fin_sep_tax = _floor_won(fin_total * fin_rate)
        if fin_total > _ZERO:
            notes.append("이자·배당 합계가 종합과세기준금액 이하라 14% 원천징수로 분리과세한다(소득세법 제14조제3항제6호).")

    # 3. 연금소득금액 (제47조의2)
    pension_ded    = _pension_income_deduction(pension, pen_doc["data"]["pension_income_deduction"])
    pension_income = pension - pension_ded

    # 4. 기타소득금액 (시행령 제87조제1호의2, 제14조제3항제8호가목)
    deemed_expense = max(_floor_won(deemed_revenue * D(str(data["other_income_deemed_expense_rate"]))), actual_expense)
    other_total    = deemed_revenue - deemed_expense + other_net
    over_limit     = other_total > D(str(data["other_income_separate_threshold"]))
    other_aggr     = over_limit or (other_income_aggregate and other_total > _ZERO)
    if other_aggr:
        other_income  = other_total
        other_sep_tax = _ZERO
        if over_limit:
            notes.append("기타소득금액이 300만원을 넘어 종합과세한다(소득세법 제14조제3항제8호가목).")
    else:
        other_income  = _ZERO
        other_sep_tax = _floor_won(other_total * D(str(data["other_income_withholding_rate"])))

    comprehensive = labor_income + business + fin_amount + pension_income + other_income

    # 5. 종합소득공제 (제50조, 제51조)
    add_rule   = data["additional_deduction"]
    basic_ded  = D(str(wh_data["personal_deduction"])) * Decimal(dependents)
    additional = (
        D(str(add_rule["elderly"])) * Decimal(elderly_count)
        + D(str(add_rule["disabled"])) * Decimal(disabled_count)
    )
    if single_parent:
        additional += D(str(add_rule["single_parent"]))
        if woman_deduction:
            notes.append("부녀자공제와 한부모공제에 모두 해당해 한부모공제만 적용한다(소득세법 제51조제1항 단서).")
    elif woman_deduction:
        if comprehensive <= D(str(add_rule["woman_income_limit"])):
            additional += D(str(add_rule["woman"]))
        else:
            notes.append("종합소득금액이 3천만원을 넘어 부녀자공제를 적용하지 않는다(소득세법 제51조제1항제3호).")
    personal = min(basic_ded + additional, comprehensive)
    if personal < basic_ded + additional:
        notes.append("인적공제 합계가 종합소득금액을 넘어 넘는 부분은 없는 것으로 한다(소득세법 제51조제4항).")

    taxable = max(comprehensive - personal - extra_ded, _ZERO)

    # 6. 산출세액 (제55조, 제62조)
    comparison: FinancialComparison | None = None
    if fin_aggr:
        aggregated_tax = _basic_rate_tax(taxable - threshold, brackets) + _floor_won(threshold * fin_rate)
        other_base     = comprehensive - fin_amount - personal - extra_ded
        separate_tax   = _floor_won(fin_total * fin_rate) + _basic_rate_tax(other_base, brackets)
        computed       = max(aggregated_tax, separate_tax)
        comparison     = {
            "aggregated_method_tax": str(aggregated_tax),
            "separate_method_tax":   str(separate_tax),
            "applied":               "aggregated" if aggregated_tax >= separate_tax else "separate",
        }
        dividend_credit = min(gross_up, max(computed - separate_tax, _ZERO))
    else:
        computed        = _basic_rate_tax(taxable, brackets)
        dividend_credit = _ZERO

    # 7. 세액공제 (제56조, 제59조, 제59조의2, 제59조의4제9항)
    labor_credit = _ZERO
    if labor_income > _ZERO and comprehensive > _ZERO:
        labor_share  = _floor_won(computed * labor_income / comprehensive)
        labor_credit = _floor_won(_labor_income_tax_credit(labor_share, salary))
        trace.step("labor_income_computed_tax", str(labor_share))

    child_credit = _child_tax_credit(children_count, birth_orders, data["child_tax_credit"])

    standard_credit = _ZERO
    if apply_standard_tax_credit:
        if salary > _ZERO:
            standard_credit = STANDARD_TAX_CREDIT
        else:
            non_wage        = data["standard_tax_credit_non_wage"]
            standard_credit = D(str(non_wage["diligent_business" if diligent_business_operator else "other"]))

    total_credits = dividend_credit + labor_credit + child_credit + standard_credit + extra_credit
    decided       = max(computed - total_credits, _ZERO)
    if total_credits > computed:
        notes.append("세액공제 합계가 산출세액을 넘어 결정세액을 0으로 한다.")
    local_tax = _floor_won(decided * _LOCAL_RATE)

    trace.step("labor_income_amount",     str(labor_income))
    trace.step("financial_income_amount", str(fin_amount))
    trace.step("dividend_gross_up",       str(gross_up))
    trace.step("pension_income_amount",   str(pension_income))
    trace.step("other_income_total",      str(other_total))
    trace.step("comprehensive_income",    str(comprehensive))
    trace.step("personal_deduction",      str(personal))
    trace.step("taxable_income",          str(taxable))
    if comparison is not None:
        trace.step("financial_comparison", comparison)
    trace.step("computed_tax",            str(computed))
    trace.step("total_tax_credits",       str(total_credits))
    trace.step("decided_tax",             str(decided))
    trace.output(str(decided + local_tax))

    resp: dict[str, Any] = {
        "labor_income_deduction":        str(labor_ded),
        "labor_income_amount":           str(labor_income),
        "business_income_amount":        str(business),
        "financial_income_total":        str(fin_total),
        "financial_income_aggregated":   fin_aggr,
        "dividend_gross_up":             str(gross_up),
        "financial_income_amount":       str(fin_amount),
        "financial_income_separate_tax": str(fin_sep_tax),
        "pension_income_deduction":      str(pension_ded),
        "pension_income_amount":         str(pension_income),
        "other_income_total":            str(other_total),
        "other_income_aggregated":       other_aggr,
        "other_income_separate_tax":     str(other_sep_tax),
        "comprehensive_income":          str(comprehensive),
        "basic_deduction":               str(basic_ded),
        "additional_deduction":          str(additional),
        "personal_deduction":            str(personal),
        "other_income_deductions":       str(extra_ded),
        "taxable_income":                str(taxable),
        "computed_tax":                  str(computed),
        "dividend_tax_credit":           str(dividend_credit),
        "labor_income_tax_credit":       str(labor_credit),
        "child_tax_credit":              str(child_credit),
        "standard_tax_credit":           str(standard_credit),
        "other_tax_credits":             str(extra_credit),
        "total_tax_credits":             str(total_credits),
        "decided_tax":                   str(decided),
        "local_income_tax":              str(local_tax),
        "total_tax":                     str(decided + local_tax),
        "notes":                         notes,
        "referenced_policies": [
            _referenced("tax/kr_income",         inc_doc),
            _referenced("tax/kr_withholding",    wh_doc),
            _referenced("tax/kr_pension_income", pen_doc),
        ],
        "policy_version":                doc["policy_version"],
        "trace":                         trace.to_dict(),
    }
    if comparison is not None:
        resp["financial_comparison"] = comparison
    return cast(TaxKrComprehensiveIncomeTaxResult, enrich_response(resp, doc))
