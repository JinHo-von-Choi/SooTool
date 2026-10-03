"""Tests for payroll.kr_national_pension_benefit.

작성자: 최진호
작성일: 2026-10-03

기대값은 국민연금법 제51조제1항(비례상수 1천분의 1천290, 20년 초과 1년마다 1천분의 50),
부칙(법률 제8541호) 제20조 연도별 비례상수, 제62조(연기 월 1천분의 6), 제63조(10년 50%, 1년마다 5%,
조기 월 1천분의 5), 국민연금공단 공시 기본연금액 산식과 2026년 지급 개시분 A값 3,193,511원,
보건복지부고시 제2026-12호 재평가율·부양가족연금액에서 직접 계산했다. 금액은 원 미만 버림.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError
from sootool.policy_mgmt.validators import validate_policy

_POLICY = (
    Path(__file__).resolve().parents[3]
    / "src" / "sootool" / "policies" / "payroll" / "kr_national_pension_benefit_2026.yaml"
)

A_2026 = Decimal("3193511")


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_national_pension_benefit", **kwargs)


def full_career(**kwargs):
    """2026~2065년 40년(480개월) 가입, B = A. 전 기간 비례상수 1.29."""
    base = {"year": 2026, "contribution_months": 480, "b_value": str(A_2026), "contribution_end_year": 2065}
    return call(**{**base, **kwargs})


def test_policy_file_validates():
    report = validate_policy(_POLICY.read_text(encoding="utf-8"), "payroll", "kr_national_pension_benefit")
    assert report["status"] == "ok", report["findings"]


class TestBasicPension:
    def test_forty_years_replaces_43_percent_of_a(self):
        """1.29 x (A + A) x (1 + 0.05 x 240/12) = 16,478,516.76원/년, 월 1,373,209원 (A의 43%)."""
        r = full_career()
        assert r["a_value"] == "3193511"
        assert Decimal(r["weighted_amount"]) == Decimal("8239258.38")
        assert Decimal(r["extension_factor"]) == Decimal("2")
        assert r["basic_pension_annual"] == "16478516"
        assert r["monthly_pension"] == "1373209"
        assert r["periods"] == [{"from_year": 2026, "to_year": None, "constant": "1.29", "b_weight": "1", "months": 480}]

    def test_twenty_years_ending_2025_uses_yearly_constants(self):
        """2006~2025 연속 240개월, B 300만원.
        (1.8 x 24 + (1.500 + 1.485 + ... + 1.245) x 12) / 240 = 1.41525, x (A + B) = 8,765,366.44원/년."""
        r = call(year=2026, contribution_months=240, b_value="3000000")
        assert [p["months"] for p in r["periods"]][:2] == [24, 12]
        assert r["periods"][0]["constant"] == "1.8"
        assert r["periods"][-1] == {"from_year": 2025, "to_year": 2025, "constant": "1.245", "b_weight": "1", "months": 12}
        assert r["basic_pension_annual"] == "8765366"
        assert r["payment_rate"] == "1"
        assert r["monthly_pension"] == "730447"

    def test_income_history_applies_revaluation_and_pre_1999_formula(self):
        """1995~2014년 월 100만원. B = sum(100만원 x 12 x 재평가율) / 240 = 2,199,900원.
        1995~1998년은 2.4 x (A + 0.75B), 1999~2007년 1.8, 2008~2014년 연도별 상수. 월 786,675원."""
        history = [{"year": y, "monthly_income": "1000000", "months": 12} for y in range(1995, 2015)]
        r = call(year=2026, income_history=history)
        assert r["input_mode"] == "income_history"
        assert Decimal(r["b_value"]) == Decimal("2199900")
        assert r["periods"][0] == {"from_year": 1988, "to_year": 1998, "constant": "2.4", "b_weight": "0.75", "months": 48}
        assert r["monthly_pension"] == "786675"


class TestContributionPeriod:
    @pytest.mark.parametrize(
        ("months", "rate", "monthly"),
        [
            (120, "0.5", "343302"),   # 10년: 기본연금액의 1천분의 500
            (180, "0.75", "514953"),  # 15년: 500 + 5년 x 50
            (239, None, "683744"),    # 0.5 + 0.05 x 119/12
            (241, "1", "689465"),     # 20년 1개월 초과: 1 + 0.05 x 1/12 가산
        ],
    )
    def test_payment_rate_by_months(self, months, rate, monthly):
        end = 2025 + (months + 11) // 12
        r = call(year=2026, contribution_months=months, b_value=str(A_2026), contribution_end_year=end)
        if rate is not None:
            assert Decimal(r["payment_rate"]) == Decimal(rate)
        assert r["monthly_pension"] == monthly

    def test_under_ten_years_is_rejected(self):
        with pytest.raises(InvalidInputError, match="반환일시금"):
            call(year=2026, contribution_months=119, b_value="3000000", contribution_end_year=2035)


class TestClaimTiming:
    def test_early_sixty_months_is_70_percent(self):
        """조기 60개월: 1 - 0.005 x 60 = 0.70. 16,478,516.76 x 0.7 / 12 = 961,246원."""
        r = full_career(claim_offset_months=-60)
        assert Decimal(r["adjustment_factor"]) == Decimal("0.7")
        assert r["monthly_pension"] == "961246"

    def test_full_deferral_sixty_months_adds_36_percent(self):
        """연기 60개월: 1 + 0.006 x 60 = 1.36. 월 1,867,565원."""
        r = full_career(claim_offset_months=60)
        assert Decimal(r["adjustment_factor"]) == Decimal("1.36")
        assert r["monthly_pension"] == "1867565"

    def test_partial_deferral_adds_only_on_deferred_share(self):
        """50% 12개월 연기: 0.5 + 0.5 x 1.072 = 1.036. 월 1,422,645원."""
        r = full_career(claim_offset_months=12, deferral_ratio="0.5")
        assert Decimal(r["adjustment_factor"]) == Decimal("1.036")
        assert r["monthly_pension"] == "1422645"

    @pytest.mark.parametrize("offset", [-61, 61])
    def test_offset_over_five_years_is_rejected(self, offset):
        with pytest.raises(InvalidInputError):
            full_career(claim_offset_months=offset)

    def test_partial_ratio_only_with_deferral(self):
        with pytest.raises(InvalidInputError):
            full_career(claim_offset_months=-12, deferral_ratio="0.5")

    def test_unlisted_ratio_is_rejected(self):
        with pytest.raises(InvalidInputError):
            full_career(claim_offset_months=12, deferral_ratio="0.55")


def test_dependent_pension_added_after_adjustment():
    """배우자 연 306,630원 + 자녀·부모 2명 x 연 204,360원. 조기 감액 대상이 아니다."""
    r = full_career(dependent_spouse=True, dependent_children_parents=2)
    assert r["dependent_pension_annual"] == "715350"
    assert r["monthly_pension"] == "1432822"
    early = full_career(claim_offset_months=-60, dependent_spouse=True, dependent_children_parents=2)
    assert early["dependent_pension_annual"] == "715350"


class TestMonthlyIncomeMode:
    def test_income_truncated_to_thousand_won(self):
        """기준소득월액 3,001,500원 -> 천원 미만 버림 3,001,000원. 0.215 x (A + B) = 1,331,819원."""
        r = full_career(b_value=None, monthly_income="3001500")
        assert r["b_value"] == "3001000"
        assert r["income_capped"] is False
        assert r["monthly_pension"] == "1331819"

    def test_cap_follows_as_of(self):
        """상한 6,370,000원(2026.1~6월) 과 6,590,000원(2026.7월~)."""
        before = full_career(b_value=None, monthly_income="10000000", as_of="2026-06-30")
        after  = full_career(b_value=None, monthly_income="10000000", as_of="2026-07-01")
        assert before["b_value"] == "6370000"
        assert after["b_value"] == "6590000"
        assert before["income_capped"] is True
        assert before["monthly_pension"] == "2056154"
        assert after["monthly_pension"] == "2103454"


class TestInputErrors:
    def test_exactly_one_income_mode(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, contribution_months=240, b_value="3000000", monthly_income="3000000")
        with pytest.raises(InvalidInputError):
            call(year=2026, contribution_months=240)

    def test_months_required_for_simple_modes(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, b_value="3000000")

    def test_history_rejects_months_argument(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, contribution_months=12, income_history=[{"year": 2020, "monthly_income": "1", "months": 12}])

    @pytest.mark.parametrize(
        "history",
        [
            [{"year": 1987, "monthly_income": "1000000", "months": 12}],
            [{"year": 2026, "monthly_income": "1000000", "months": 12}],
            [{"year": 2020, "monthly_income": "1000000", "months": 13}],
            [{"year": 2020, "monthly_income": "1000000"}],
            [{"year": 2020, "monthly_income": "1000000", "months": 12}] * 2,
        ],
    )
    def test_invalid_history_entries(self, history):
        with pytest.raises(InvalidInputError):
            call(year=2026, income_history=history)

    def test_backward_allocation_before_1988_is_rejected(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, contribution_months=240, b_value="3000000", contribution_end_year=2000)


class TestPolicyPeriod:
    def test_policy_fields(self):
        r = full_career()
        assert r["policy_effective_date"] == "2026-01-01"
        assert r["policy_effective_to"] == "2026-12-31"
        assert any("제51조" in c.get("article", "") for c in r["policy_citations"])

    def test_as_of_outside_2026_is_not_in_effect(self):
        with pytest.raises(PolicyNotInEffectError):
            full_career(as_of="2027-01-15")

    def test_unpublished_year_is_unsupported(self):
        with pytest.raises(UnsupportedPolicyError):
            full_career(year=2027)
