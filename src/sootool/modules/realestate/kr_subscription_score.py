"""Korean housing subscription point score (청약 가점제 점수).

Author: 최진호
Date: 2026-10-03

주택공급에 관한 규칙 별표 1 제2호나목:
  무주택기간       상한 32점 (1년 미만 2점, 1년마다 2점, 15년 이상 32점)
  부양가족 수      상한 35점 (0명 5점, 1명마다 5점, 6명 이상 35점)
  주택청약종합저축 상한 17점 (6개월 미만 1점, 1년 미만 2점, 이후 1년마다 1점, 15년 이상 17점)
  합계 상한 84점
별표 1 비고 제2호: 배우자 가입기간의 50% 기간에 대한 점수(3점 한도)를 가입기간 점수에 합산, 합산 17점 한도.

무주택기간이 기산되지 않은 경우(주택 소유 세대, 만 30세 미만 미혼)는 별표의 가점구분에 해당하지 않아
청약홈(한국부동산원) 운영 기준대로 0점으로 본다.

기간과 인원은 입주자모집공고일 현재 별표 1 제1호 기준으로 산정한 값을 입력받는다. 기간 산정,
부양가족 인정 요건, 가점제 적용 대상 여부(규칙 제28조제6항)는 판정하지 않는다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response


class SubscriptionScoreResult(PolicyResult):
    homeless_points:       int
    dependents_points:     int
    savings_points:        int
    spouse_savings_points: int
    savings_total_points:  int
    total_points:          int
    max_total_points:      int


def _non_negative_int(name: str, value: Any) -> int:
    """0 이상의 정수 입력을 검증한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidInputError(f"{name}는 0 이상의 정수여야 합니다.")
    return int(value)


def _bracket_points(months: Decimal, brackets: list[dict[str, Any]]) -> int:
    """기간(개월)이 ``below_months`` 미만인 첫 구간의 점수. 상한 없는 마지막 구간이 나머지를 받는다."""
    for row in brackets:
        below = row.get("below_months")
        if below is None or months < D(str(below)):
            return int(row["points"])
    return int(brackets[-1]["points"])


@REGISTRY.tool(
    namespace="realestate",
    name="kr_subscription_score",
    description=(
        "주택공급에 관한 규칙 별표 1의 청약 가점제 점수(무주택기간 32, 부양가족 35, 청약저축 가입기간 17, 합계 84점)를 계산한다. "
        "기간은 입주자모집공고일 현재 개월 수 정수, 부양가족은 인원 정수로 넣는다. 배우자 가입기간은 50%로 환산해 3점 한도로 "
        "합산하고 저축 점수는 17점 한도다. 주택 소유 세대나 만 30세 미만 미혼은 homeless_period_applicable=false 로 0점이다. "
        "만 나이 전체를 무주택기간으로 넣는 것은 오용이며 30세 또는 혼인신고일부터 센다."
    ),
    version="1.0.0",
    policy=True,
)
def realestate_kr_subscription_score(
    year:                       int,
    homeless_months:            int,
    dependents:                 int,
    savings_months:             int,
    homeless_period_applicable: bool       = True,
    spouse_savings_months:      int | None = None,
) -> SubscriptionScoreResult:
    """Calculate the subscription point score under 별표 1.

    Args:
        year:                       입주자모집공고 연도.
        homeless_months:            무주택기간(개월). 별표 1 제1호가목3) 기준.
        dependents:                 부양가족 수(명). 별표 1 제1호나목 기준.
        savings_months:             본인 주택청약종합저축 가입기간(개월). 최초 가입일 기준.
        homeless_period_applicable: 무주택기간 기산 여부. 주택 소유 세대 또는 만 30세 미만 미혼이면 False(0점).
        spouse_savings_months:      배우자 주택청약종합저축 가입기간(개월). 미가입이면 생략.
                                    특별공급에는 합산하지 않는다(별표 1 비고 제2호).

    Returns:
        {homeless_points, dependents_points, savings_points, spouse_savings_points,
         savings_total_points, total_points, max_total_points, policy_version, trace}
    """
    trace = CalcTrace(
        tool="realestate.kr_subscription_score",
        formula=(
            "총점 = 무주택기간 점수 + 부양가족 점수 + min(본인 가입기간 점수 + min(배우자 50% 기간 점수, 3), 17)"
        ),
    )

    homeless = _non_negative_int("homeless_months", homeless_months)
    family   = _non_negative_int("dependents", dependents)
    savings  = _non_negative_int("savings_months", savings_months)
    spouse   = (
        _non_negative_int("spouse_savings_months", spouse_savings_months)
        if spouse_savings_months is not None else None
    )

    policy_doc = policy_load("realestate", "kr_subscription", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    trace.input("year",                       year)
    trace.input("homeless_months",            homeless_months)
    trace.input("dependents",                 dependents)
    trace.input("savings_months",             savings_months)
    trace.input("homeless_period_applicable", homeless_period_applicable)
    trace.input("spouse_savings_months",      spouse_savings_months)

    homeless_cfg = data["homeless_period"]
    if homeless_period_applicable:
        homeless_pts = _bracket_points(Decimal(homeless), homeless_cfg["brackets"])
    else:
        homeless_pts = int(homeless_cfg["not_applicable_points"])

    family_table   = data["dependents"]["points_by_count"]
    dependents_pts = int(family_table[min(family, len(family_table) - 1)])

    savings_cfg = data["savings_period"]
    savings_pts = _bracket_points(Decimal(savings), savings_cfg["brackets"])

    spouse_cfg = data["spouse_savings"]
    spouse_pts = 0
    if spouse is not None:
        spouse_period = Decimal(spouse) * D(str(spouse_cfg["period_ratio"]))
        spouse_pts    = min(_bracket_points(spouse_period, savings_cfg["brackets"]), int(spouse_cfg["max_points"]))
        trace.step("spouse_counted_months", str(spouse_period))

    savings_total = min(savings_pts + spouse_pts, int(savings_cfg["max_points"]))
    total         = homeless_pts + dependents_pts + savings_total

    trace.step("homeless_points",       homeless_pts)
    trace.step("dependents_points",     dependents_pts)
    trace.step("savings_points",        savings_pts)
    trace.step("spouse_savings_points", spouse_pts)
    trace.step("savings_total_points",  savings_total)
    trace.output(total)

    resp: dict[str, Any] = {
        "homeless_points":       homeless_pts,
        "dependents_points":     dependents_pts,
        "savings_points":        savings_pts,
        "spouse_savings_points": spouse_pts,
        "savings_total_points":  savings_total,
        "total_points":          total,
        "max_total_points":      int(data["max_total_points"]),
        "policy_version":        pv,
        "trace":                 trace.to_dict(),
    }
    return cast(SubscriptionScoreResult, enrich_response(resp, policy_doc))
