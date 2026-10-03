"""Tests for payroll.kr_health_income_premium.

작성자: 최진호
작성일: 2026-10-03

기대값은 국민건강보험법 제71조제1항((연간 보수 외 소득 - 2천만원) x 1/12), 시행령 제41조제4항,
시행규칙 제44조(이자·배당 1천만원 이하 제외, 근로·연금소득 100분의 50), 시행령 제44조 보험료율 7.19%,
보건복지부고시 제2025-222호(소득월액 보험료 상한 4,591,740원, 보수월액보험료 하한 20,160원),
노인장기요양보험법 시행령 제4조 0.9448%와 같은 법 제9조제1항(2026년 11월분부터 비율 0.1314),
시행령 제36조·제39조(정산, 분할납부 기준 2026.10.1. 개정)에서 직접 계산했다. 보험료는 원 미만 버림.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policy_mgmt.validators import validate_policy

_POLICY_DIR = Path(__file__).resolve().parents[3] / "src" / "sootool" / "policies" / "payroll"


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_health_income_premium", **kwargs)


def income(**kwargs):
    return call(year=2026, **kwargs)["income_premium"]


@pytest.mark.parametrize(
    "name", ["kr_health_income_premium_2026.yaml", "kr_health_income_premium_2026@2026-10-01.yaml"],
)
def test_policy_files_validate(name):
    report = validate_policy((_POLICY_DIR / name).read_text(encoding="utf-8"), "payroll", "kr_health_income_premium")
    assert report["status"] == "ok", report["findings"]


class TestIncomePremium:
    def test_business_income_over_threshold(self):
        """사업소득 3천만원: (3천만 - 2천만) / 12 = 833,333.33 x 7.19% = 59,916원.
        장기요양: 2026.3월분 비율 0.9448/7.19 -> 7,873원, 11월분 비율 0.1314 -> 7,872원."""
        march = income(business_income="30000000", as_of="2026-03-01")
        nov   = income(business_income="30000000", as_of="2026-11-01")
        assert march["subject"] is True
        assert march["health_premium"] == "59916"
        assert march["long_term_care_premium"] == "7873"
        assert march["total"] == "67789"
        assert nov["long_term_care_premium"] == "7872"

    def test_wage_and_pension_evaluated_at_half(self):
        """연금 2천만원 + 이자 1,500만원: X = 3,500만원, 평가 = (1,500만 + 2천만 x 0.5) / 3,500만.
        소득월액 = 1,500만 / 12 x 25/35 = 892,857.14, 보험료 64,196원."""
        r = income(pension_income="20000000", interest_income="15000000")
        assert r["financial_income_included"] is True
        assert Decimal(r["evaluation_factor"]).quantize(Decimal("0.000001")) == Decimal("0.714286")
        assert r["health_premium"] == "64196"

    def test_wage_only(self):
        """보수 외 근로소득 6천만원: (6천만 - 2천만) / 12 x 0.5 x 7.19% = 119,833원."""
        assert income(wage_income="60000000")["health_premium"] == "119833"

    def test_small_financial_income_is_excluded(self):
        """이자 900만원은 합산 제외: X = 사업 2,500만원. (500만 / 12) x 7.19% = 29,958원."""
        r = income(interest_income="9000000", business_income="25000000")
        assert r["financial_income_included"] is False
        assert r["annual_non_salary_income"] == "25000000"
        assert r["health_premium"] == "29958"

    def test_financial_income_just_over_ten_million_counts(self):
        r = income(interest_income="10000001", business_income="10000000")
        assert r["financial_income_included"] is True
        assert r["subject"] is True

    @pytest.mark.parametrize(("amount", "subject"), [("20000000", False), ("20000001", True)])
    def test_threshold_boundary(self, amount, subject):
        r = income(business_income=amount)
        assert r["subject"] is subject
        if not subject:
            assert r["total"] == "0"

    def test_monthly_cap(self):
        """사업소득 10억원: 98천만 / 12 x 7.19% = 5,871,833원 > 상한 4,591,740원."""
        r = income(business_income="1000000000", as_of="2026-03-01")
        assert r["premium_capped"] is True
        assert r["health_premium"] == "4591740"
        assert r["long_term_care_premium"] == "603376"

    def test_negative_income_rejected(self):
        with pytest.raises(InvalidInputError):
            income(business_income="-1")


class TestSettlement:
    def test_annual_settlement_difference(self):
        """보수총액 6천만원 / 12 = 500만원. 근로자 179,750원 x 12 = 2,157,000원.
        장기요양 1~10월 179,750 x 0.9448 / 7.19 = 23,620원, 11·12월 x 0.1314 = 23,619.15 -> 원 단위 절사 23,610원
        -> 10 x 23,620 + 2 x 23,610 = 283,420원."""
        r = call(
            year=2026, annual_remuneration_total="60000000",
            health_premium_paid="2040000", ltc_premium_paid="264000",
        )["settlement"]
        assert r["remuneration_monthly"] == "5000000"
        assert r["recalculated_health_premium"] == "2157000"
        assert r["recalculated_long_term_care"] == "283420"
        assert r["health_difference"] == "117000"
        assert r["long_term_care_difference"] == "19420"
        assert r["total_difference"] == "136420"

    def test_long_term_care_ratio_changes_in_november(self):
        """보수월액 280만원: 건강 100,660원. 장기요양 9·10월 100,660 x 0.9448 / 7.19 = 13,226.9 -> 13,220원(원 단위 절사),
        11·12월 x 0.1314 = 13,226.7 -> 13,220원."""
        r = call(
            year=2026, annual_remuneration_total="11200000", start_month=9, end_month=12,
            health_premium_paid="402640", ltc_premium_paid="52880",
        )["settlement"]
        assert r["months_worked"] == 4
        assert [m["long_term_care_premium"] for m in r["months"]] == ["13220", "13220", "13220", "13220"]
        assert r["total_difference"] == "0"
        assert r["installment_eligible"] is False

    def test_refund_is_negative(self):
        r = call(
            year=2026, annual_remuneration_total="24000000",
            health_premium_paid="1200000", ltc_premium_paid="150000",
        )["settlement"]
        assert Decimal(r["health_difference"]) < 0
        assert r["installment_eligible"] is False

    def test_premium_floor_applies(self):
        """보수월액 20만원 x 3.595% = 7,190원 < 하한 20,160원의 절반 10,080원."""
        r = call(
            year=2026, annual_remuneration_total="200000", start_month=1, end_month=1,
            health_premium_paid="0", ltc_premium_paid="0",
        )["settlement"]
        assert r["months"][0]["health_premium"] == "10080"

    def test_installment_rule_changes_on_2026_10_01(self):
        """추가징수 건강보험료 117,000원. 2026.9.30.까지는 월 보험료 179,750원 이상이어야 분할 가능,
        2026.10.1.부터는 보수월액보험료 하한액 20,160원 이상이면 분할 가능 (12회 이내)."""
        args = {
            "year": 2026, "annual_remuneration_total": "60000000",
            "health_premium_paid": "2040000", "ltc_premium_paid": "264000",
        }
        before = call(as_of="2026-09-30", **args)["settlement"]
        after  = call(as_of="2026-10-01", **args)["settlement"]
        assert before["installment_basis"] == "monthly_premium"
        assert before["installment_threshold"] == "179750"
        assert before["installment_eligible"] is False
        assert after["installment_basis"] == "premium_floor"
        assert after["installment_threshold"] == "20160"
        assert after["installment_eligible"] is True
        assert after["max_installments"] == 12

    def test_settlement_omitted_without_remuneration(self):
        assert "settlement" not in call(year=2026, business_income="30000000")

    def test_paid_amounts_required(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, annual_remuneration_total="60000000", health_premium_paid="1")

    def test_paid_without_remuneration_rejected(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, health_premium_paid="1", ltc_premium_paid="1")

    @pytest.mark.parametrize(("start", "end"), [(0, 12), (5, 4), (1, 13)])
    def test_month_range(self, start, end):
        with pytest.raises(InvalidInputError):
            call(
                year=2026, annual_remuneration_total="1000000", start_month=start, end_month=end,
                health_premium_paid="0", ltc_premium_paid="0",
            )


def test_policy_version_follows_as_of():
    assert call(year=2026, as_of="2026-09-30")["policy_effective_date"] == "2026-01-01"
    assert call(year=2026, as_of="2026-10-01")["policy_effective_date"] == "2026-10-01"
