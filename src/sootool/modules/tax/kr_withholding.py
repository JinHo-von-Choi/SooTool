"""Korean withholding tax (근로소득 간이세액표) calculator.

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

근로소득 원천징수세액은 소득세법 시행령 제194조제1항에 따라 별표 2 근로소득 간이세액표
해당란의 세액을 기준으로 한다. 표는 정책 YAML(simple_tax_table)에 데이터로 둔다.

  1. 월급여액(비과세 및 학자금 제외, 원)을 천원 단위로 환산해 [이상, 미만) 행을 찾는다.
     770천원 미만은 0원. 정확히 10,000천원이면 10,000천원 행.
  2. 10,000천원 초과는 별표 2 하단 산식: 10,000천원 세액 + 구간 가산액 + 초과액 x 비율 x 세율.
  3. 공제대상가족 11명 초과는 별표 2 제4호: 세액(11명) - (세액(10명) - 세액(11명)) x 초과 인원.
  4. 8세 이상 20세 이하 자녀 수별 차감(별표 2 제3호). 결과가 음수면 0원.
"""
from __future__ import annotations

import bisect
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError, PolicyFormatError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


def _calc_labor_income_deduction(
    annual_income: Decimal,
    brackets:      list[dict[str, Any]],
    cap:           Decimal | None = None,
) -> Decimal:
    """근로소득공제 계산 (소득세법 제47조제1항, 누진 공제 구간).

    cap 이 주어지면 공제액은 cap 을 넘지 않는다(같은 항 단서, 2천만원).
    """
    lower     = Decimal("0")
    deduction = Decimal("0")
    for bracket in brackets:
        upper_raw = bracket["upper"]
        rate      = D(str(bracket["rate"]))
        upper     = None if upper_raw is None else D(str(upper_raw))

        if annual_income <= lower:
            break

        ceiling    = annual_income if upper is None else min(annual_income, upper)
        taxable_in = ceiling - lower
        if taxable_in > Decimal("0"):
            deduction += taxable_in * rate

        if upper is None:
            break
        lower = upper

    if cap is not None and deduction > cap:
        return cap
    return deduction


@dataclass(frozen=True)
class SimpleTaxLookup:
    """간이세액표 조회 결과.

    tax:             자녀 차감 후 월 원천징수세액(원)
    table_tax:       자녀 차감 전 간이세액표 세액(원)
    child_reduction: 실제로 차감한 자녀 공제액(원)
    method:          below_min | table_row | at_upper | above_upper
    salary_k:        조회에 쓴 월급여액(천원, 천원 미만 버림)
    row:             조회한 행 {lower_k, upper_k} 또는 산식 구간 {over_k, upper_k}
    steps:           (단계 이름, 값) 목록
    """

    tax:             Decimal
    table_tax:       Decimal
    child_reduction: Decimal
    method:          str
    salary_k:        Decimal
    row:             dict[str, Any] | None
    steps:           list[tuple[str, Any]] = field(default_factory=list)


def _table(policy_data: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        table = policy_data["simple_tax_table"]
        policy_data["child_reduction_monthly"]
    except KeyError as exc:
        raise PolicyFormatError(f"kr_withholding 정책에 간이세액표 키가 없습니다: {exc}") from exc
    return table  # type: ignore[no-any-return]


def _family_tax(taxes: list[Any], dependents: int, max_family: int, floor_zero: bool) -> Decimal:
    """한 행의 가족 수별 세액. 11명 초과는 별표 2 제4호 산식."""
    if dependents <= max_family:
        return D(str(taxes[dependents - 1]))
    last  = D(str(taxes[max_family - 1]))
    prev  = D(str(taxes[max_family - 2]))
    value = last - (prev - last) * Decimal(dependents - max_family)
    if floor_zero and value < Decimal("0"):
        return Decimal("0")
    return value


def _child_reduction(children: int, rule: Mapping[str, Any]) -> Decimal:
    """별표 2 제3호 자녀 수별 차감액."""
    if children <= 0:
        return Decimal("0")
    if children == 1:
        return D(str(rule["one"]))
    two = D(str(rule["two"]))
    return two + D(str(rule["per_child_over_two"])) * Decimal(children - 2)


def lookup_simple_tax(
    monthly_salary: Decimal,
    dependents:     int,
    children_8_20:  int,
    policy_data:    Mapping[str, Any],
) -> SimpleTaxLookup:
    """근로소득 간이세액표(소득세법 시행령 별표 2)로 월 원천징수세액을 구한다.

    Args:
        monthly_salary: 월급여액(원). 비과세 소득과 학자금을 제외한 금액
        dependents:     공제대상가족 수(본인 포함, 1 이상)
        children_8_20:  공제대상가족 중 8세 이상 20세 이하 자녀 수(0 이상, dependents - 1 이하)
        policy_data:    kr_withholding 정책 data

    시간 복잡도: 행 수 n 에 대해 O(n) (행 하한 목록 구성) + O(log n) 조회.
    """
    if monthly_salary < Decimal("0"):
        raise InvalidInputError("monthly_salary는 0 이상이어야 합니다.")
    if dependents < 1:
        raise InvalidInputError("dependents는 1 이상이어야 합니다 (본인 포함).")
    if children_8_20 < 0:
        raise InvalidInputError("children_8_20은 0 이상이어야 합니다.")
    if children_8_20 > dependents - 1:
        raise InvalidInputError("children_8_20은 본인을 제외한 공제대상가족 수(dependents - 1)를 넘을 수 없습니다.")

    table      = _table(policy_data)
    unit       = D(str(table["salary_unit_krw"]))
    max_family = int(table["max_family"])
    floor_zero = bool(policy_data.get("family_over_max", {}).get("floor_zero", True))
    rows       = table["rows"]
    upper_k    = D(str(table["at_upper_salary_k"]))
    salary_k   = round_apply(monthly_salary / unit, 0, RoundingPolicy.DOWN)

    steps: list[tuple[str, Any]] = [("salary_k", str(salary_k))]
    row_info: dict[str, Any] | None
    min_k = D(str(rows[0][0]))

    if salary_k < min_k:
        method, row_info = "below_min", None
        table_tax = Decimal("0")
    elif monthly_salary < upper_k * unit:
        lowers = [D(str(r[0])) for r in rows]
        index  = bisect.bisect_right(lowers, salary_k) - 1
        lo, hi, taxes = rows[index]
        method, row_info = "table_row", {"lower_k": lo, "upper_k": hi}
        table_tax = _family_tax(taxes, dependents, max_family, floor_zero)
    else:
        base = _family_tax(table["at_upper"], dependents, max_family, floor_zero)
        if monthly_salary == upper_k * unit:
            method, row_info = "at_upper", {"lower_k": int(upper_k), "upper_k": int(upper_k)}
            table_tax = base
        else:
            segment = next(
                s for s in table["above_upper"]
                if s["upper_k"] is None or monthly_salary <= D(str(s["upper_k"])) * unit
            )
            excess    = monthly_salary - D(str(segment["over_k"])) * unit
            increment = D(str(segment["add"])) + excess * D(str(segment["factor"])) * D(str(segment["rate"]))
            rounding  = table["above_upper_rounding"]
            raw_tax   = base + increment
            table_tax = round_apply(raw_tax, int(rounding["decimals"]), RoundingPolicy(str(rounding["mode"])))
            method    = "above_upper"
            row_info  = {"over_k": segment["over_k"], "upper_k": segment["upper_k"]}
            steps.append(("at_upper_tax", str(base)))
            steps.append(("excess", str(excess)))
            steps.append(("above_upper_increment", str(increment)))
            steps.append(("above_upper_raw_tax", str(raw_tax)))

    steps.append(("lookup_method", method))
    if row_info is not None:
        steps.append(("table_row", row_info))
    if dependents > max_family:
        steps.append(("family_over_max", dependents - max_family))
    steps.append(("table_tax", str(table_tax)))

    reduction = _child_reduction(children_8_20, policy_data["child_reduction_monthly"])
    tax       = table_tax - reduction
    if tax < Decimal("0"):
        tax = Decimal("0")
    applied = table_tax - tax
    steps.append(("child_reduction_rule", str(reduction)))
    steps.append(("child_reduction_applied", str(applied)))

    return SimpleTaxLookup(
        tax=tax,
        table_tax=table_tax,
        child_reduction=applied,
        method=method,
        salary_k=salary_k,
        row=row_info,
        steps=steps,
    )


def monthly_withholding_tax(
    monthly_salary: Decimal,
    dependents:     int,
    children_8_20:  int,
    policy_data:    Mapping[str, Any],
) -> Decimal:
    """간이세액표 기준 월 원천징수세액(원). 인자는 lookup_simple_tax 와 같다."""
    return lookup_simple_tax(monthly_salary, dependents, children_8_20, policy_data).tax


@REGISTRY.tool(
    namespace="tax",
    name="kr_withholding_simple",
    description=(
        "근로소득 월 원천징수세액 계산. 소득세법 시행령 별표 2 근로소득 간이세액표 조회 "
        "(10,000천원 초과 산식, 공제대상가족 11명 초과 규정, 8세 이상 20세 이하 자녀 차감 포함)."
    ),
    version="2.0.0",
    policy=True,
)
def tax_kr_withholding_simple(
    monthly_salary: str,
    dependents:     int,
    year:           int,
    children_8_20:  int = 0,
) -> dict[str, Any]:
    """Calculate monthly withholding tax from the statutory 간이세액표.

    Args:
        monthly_salary: 월급여액 (Decimal string, 원). 비과세 소득과 학자금 제외
        dependents:     공제대상가족 수 (본인 포함, 최소 1. 본인과 배우자도 각각 1명)
        year:           과세연도
        children_8_20:  공제대상가족 중 8세 이상 20세 이하 자녀 수 (기본 0)

    Returns:
        {withheld_tax, table_tax, child_reduction, lookup, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.kr_withholding_simple",
        formula=(
            "월급여액(천원) → 간이세액표 행[이상, 미만) 또는 10,000천원 초과 산식 → "
            "가족 11명 초과 조정 → 8세 이상 20세 이하 자녀 차감(음수면 0)"
        ),
    )

    monthly = D(monthly_salary)
    if monthly < Decimal("0"):
        raise InvalidInputError("monthly_salary는 0 이상이어야 합니다.")
    if dependents < 1:
        raise InvalidInputError("dependents는 1 이상이어야 합니다 (본인 포함).")

    policy_doc = policy_load("tax", "kr_withholding", year)
    pv         = policy_doc["policy_version"]

    trace.input("monthly_salary", monthly_salary)
    trace.input("dependents",     dependents)
    trace.input("children_8_20",  children_8_20)
    trace.input("year",           year)

    result = lookup_simple_tax(monthly, dependents, children_8_20, policy_doc["data"])
    for label, value in result.steps:
        trace.step(label, value)
    trace.output(str(result.tax))

    resp = {
        "withheld_tax":    str(result.tax),
        "table_tax":       str(result.table_tax),
        "child_reduction": str(result.child_reduction),
        "lookup": {
            "method":   result.method,
            "salary_k": str(result.salary_k),
            "row":      result.row,
        },
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
    return enrich_response(resp, policy_doc)
