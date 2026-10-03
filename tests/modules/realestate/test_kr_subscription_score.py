"""Tests for realestate.kr_subscription_score (청약 가점제 점수).

기대값은 주택공급에 관한 규칙 별표 1 제2호나목 가점 산정기준 표와 비고 제2호를 그대로 적용한 값이다.
무주택기간이 기산되지 않은 경우의 0점은 청약홈(한국부동산원) 청약가점계산 운영 기준이다.
"""
from __future__ import annotations

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    base = {"year": 2026, "homeless_months": 0, "dependents": 0, "savings_months": 0}
    base.update(kwargs)
    return REGISTRY.invoke("realestate.kr_subscription_score", **base)


class TestTotals:
    def test_maximum_is_84(self):
        r = call(homeless_months=180, dependents=6, savings_months=180)
        assert (r["homeless_points"], r["dependents_points"], r["savings_total_points"]) == (32, 35, 17)
        assert r["total_points"] == 84
        assert r["max_total_points"] == 84

    def test_minimum_with_started_homeless_period(self):
        """무주택 1년 미만 2점, 부양가족 0명 5점, 가입 6개월 미만 1점."""
        r = call()
        assert r["total_points"] == 8

    def test_homeless_period_not_started_is_zero(self):
        r = call(homeless_months=60, homeless_period_applicable=False)
        assert r["homeless_points"] == 0
        assert r["total_points"] == 6

    def test_typical_case(self):
        """무주택 8년 4개월 18점, 부양가족 3명 20점, 가입 10년 10개월 12점 = 50점."""
        r = call(homeless_months=100, dependents=3, savings_months=130)
        assert r["total_points"] == 50


class TestBrackets:
    @pytest.mark.parametrize("months, points", [
        (11, 2), (12, 4), (23, 4), (24, 6), (95, 16), (96, 18), (179, 30), (180, 32), (400, 32),
    ])
    def test_homeless_period(self, months, points):
        assert call(homeless_months=months)["homeless_points"] == points

    @pytest.mark.parametrize("count, points", [(0, 5), (1, 10), (3, 20), (5, 30), (6, 35), (9, 35)])
    def test_dependents(self, count, points):
        assert call(dependents=count)["dependents_points"] == points

    @pytest.mark.parametrize("months, points", [
        (0, 1), (5, 1), (6, 2), (11, 2), (12, 3), (23, 3), (24, 4), (179, 16), (180, 17), (300, 17),
    ])
    def test_savings_period(self, months, points):
        assert call(savings_months=months)["savings_points"] == points


class TestSpouseSavings:
    """배우자 가입기간의 50% 기간 점수, 3점 한도, 합산 17점 한도 (별표 1 비고 제2호)."""

    @pytest.mark.parametrize("spouse_months, points", [
        (0, 1),      # 0개월 -> 6개월 미만 1점
        (11, 1),     # 5.5개월 -> 6개월 미만 1점
        (12, 2),     # 6개월 -> 6개월 이상 1년 미만 2점
        (24, 3),     # 12개월 -> 1년 이상 2년 미만 3점
        (120, 3),    # 60개월 -> 6점이지만 3점 한도
    ])
    def test_spouse_points(self, spouse_months, points):
        r = call(savings_months=0, spouse_savings_months=spouse_months)
        assert r["spouse_savings_points"] == points
        assert r["savings_total_points"] == 1 + points

    def test_no_spouse_account_adds_nothing(self):
        assert call(savings_months=60)["spouse_savings_points"] == 0

    def test_combined_cap_is_17(self):
        """본인 14년 2개월 16점 + 배우자 3점 = 19 -> 17점."""
        r = call(savings_months=170, spouse_savings_months=120)
        assert r["savings_points"] == 16
        assert r["savings_total_points"] == 17


class TestErrorsAndPolicy:
    @pytest.mark.parametrize("kwargs", [
        {"homeless_months": -1},
        {"dependents": -1},
        {"savings_months": True},
        {"spouse_savings_months": -3},
    ])
    def test_invalid_inputs(self, kwargs):
        with pytest.raises(InvalidInputError):
            call(**kwargs)

    def test_as_of_before_effective_date(self):
        with pytest.raises(PolicyNotInEffectError):
            call(as_of="2025-12-31")

    def test_citations_are_returned(self):
        r = call(as_of="2026-10-03")
        assert any(c.get("article") == "별표 1 제2호나목" for c in r["policy_citations"])
