"""Korean education expense tax credit (교육비 세액공제) calculator.

Author: 최진호
Date: 2026-04-24

소득세법 제59조의4 제3항 교육비 세액공제:
  - 근로자 본인: 15%, 한도 없음
  - 영유아(취학 전): 1인당 연 300만원 한도 15%
  - 초·중·고 자녀: 1인당 연 300만원 한도 15%
  - 대학(원 제외): 1인당 연 900만원 한도 15%
  - 장애인 특수교육비: 한도 없음 15%

범주별 지출액과 해당 인원수를 받아서 인당 한도를 적용한다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_CATEGORIES: tuple[str, ...] = (
    "self",
    "preschool",
    "elementary",
    "middle_high",
    "university",
    "disabled_special",
)


class EducationCategoryCredit(TypedDict):
    """범주별 지출, 인원, 공제 대상액, 세액공제액. 인원은 문자열로 반환된다."""

    expense:    str
    count:      str
    qualifying: str
    credit:     str


class KrEducationDeductionResult(PolicyResult):
    per_category: dict[str, EducationCategoryCredit]
    total_credit: str


@REGISTRY.tool(
    namespace="payroll",
    name="kr_education_deduction",
    description=(
        "교육비 세액공제(소득세법 제59조의4제3항)를 구한다. expenses 는 self, preschool, elementary, middle_high, "
        "university, disabled_special 별 지출액(원 문자열), counts 는 범주별 인원이다. 공제율 15%를 정책의 인당 한도"
        "(영유아·초중고 300만원, 대학 900만원, 본인·장애인 특수교육 무한도)에 인원을 곱한 한도까지 적용해 원 미만 버린다. "
        "여러 자녀 지출을 한 범주에 합치고 counts 를 생략하면 1명분 한도만 적용된다."
    ),
    version="1.0.0",
    policy=True,
)
def payroll_kr_education_deduction(
    expenses:  dict[str, str],
    year:      int,
    counts:    dict[str, int] | None = None,
) -> KrEducationDeductionResult:
    """Calculate education expense tax credit.

    Args:
        expenses: 범주별 지출액 dict. keys:
                  self / preschool / elementary / middle_high / university / disabled_special.
                  값은 Decimal string(원).
        year:     과세연도.
        counts:   범주별 대상 인원 수. 한도는 인당 한도로 적용. 기본 1명.

    Returns:
        {per_category, total_credit, policy_version, trace}
    """
    trace = CalcTrace(
        tool="payroll.kr_education_deduction",
        formula=(
            "per_category_credit = min(expense, per_person_limit × count) × 15%; "
            "self/disabled_special 한도 없음"
        ),
    )

    if not isinstance(expenses, dict):
        raise InvalidInputError("expenses는 dict[str, str]이어야 합니다.")

    counts_in = counts or {}
    if not isinstance(counts_in, dict):
        raise InvalidInputError("counts는 dict[str, int]이어야 합니다.")

    # 입력 검증 및 기본값 채우기
    parsed_expenses: dict[str, Decimal] = {}
    parsed_counts:   dict[str, int]     = {}
    for cat in _CATEGORIES:
        exp_raw = expenses.get(cat, "0")
        try:
            exp_val = D(str(exp_raw))
        except Exception as exc:
            raise InvalidInputError(f"expenses['{cat}']를 Decimal로 변환할 수 없습니다.") from exc
        if exp_val < Decimal("0"):
            raise InvalidInputError(f"expenses['{cat}']는 0 이상이어야 합니다.")
        parsed_expenses[cat] = exp_val

        cnt_val = counts_in.get(cat, 1 if exp_val > Decimal("0") else 0)
        if not isinstance(cnt_val, int):
            raise InvalidInputError(f"counts['{cat}']는 int이어야 합니다.")
        if cnt_val < 0:
            raise InvalidInputError(f"counts['{cat}']는 0 이상이어야 합니다.")
        parsed_counts[cat] = cnt_val

    # 알 수 없는 카테고리 차단
    unknown = set(expenses.keys()) - set(_CATEGORIES)
    if unknown:
        raise InvalidInputError(
            f"지원하지 않는 교육비 카테고리: {sorted(unknown)}. "
            f"허용: {list(_CATEGORIES)}"
        )
    unknown_c = set(counts_in.keys()) - set(_CATEGORIES)
    if unknown_c:
        raise InvalidInputError(
            f"지원하지 않는 counts 카테고리: {sorted(unknown_c)}."
        )

    policy_doc = policy_load("payroll", "kr_yearend_deductions", year)
    data       = policy_doc["data"]["education"]
    pv         = policy_doc["policy_version"]

    credit_rate = D(str(data["credit_rate"]))
    limits_cfg: dict[str, Any] = data["limits"]

    trace.input("expenses", {k: str(v) for k, v in parsed_expenses.items()})
    trace.input("counts",   parsed_counts)
    trace.input("year",     year)

    per_category: dict[str, EducationCategoryCredit] = {}
    total_credit = Decimal("0")

    for cat in _CATEGORIES:
        exp = parsed_expenses[cat]
        cnt = parsed_counts[cat]
        limit_raw = limits_cfg.get(cat)

        if limit_raw is None:
            # 한도 없음
            qualifying = exp
        else:
            per_person = D(str(limit_raw))
            cap = per_person * Decimal(str(cnt))
            qualifying = exp if exp <= cap else cap

        credit = round_apply(qualifying * credit_rate, 0, RoundingPolicy.DOWN)
        total_credit += credit

        per_category[cat] = {
            "expense":    str(exp),
            "count":      str(cnt),
            "qualifying": str(qualifying),
            "credit":     str(credit),
        }

    trace.step("per_category",  per_category)
    trace.output(str(total_credit))

    resp: dict[str, Any] = {
        "per_category":   per_category,
        "total_credit":   str(total_credit),
        "policy_version": pv,
        "trace":          trace.to_dict(),
    }
    return cast(KrEducationDeductionResult, enrich_response(resp, policy_doc))
