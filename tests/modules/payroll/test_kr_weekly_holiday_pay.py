"""Tests for payroll.kr_weekly_holiday_pay.

Author: 최진호
Date: 2026-10-03

기대값은 근로기준법 제18조제3항(4주 평균 1주 15시간 미만 미적용), 제55조제1항, 제50조제2항(1일 8시간),
시행령 제30조제1항(개근), 별표 2 제2호나목(1일 소정근로시간 = 4주 소정근로시간 / 4주 통상 근로자 총 소정근로일 수)과
2026년 적용 최저임금 고시(고용노동부고시 제2025-47호) 시간급 10,320원으로 직접 계산했다.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError
from sootool.policy_mgmt.validators import validate_policy

_POLICY_DIR = Path(__file__).resolve().parents[3] / "src" / "sootool" / "policies" / "payroll"


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_weekly_holiday_pay", **kwargs)


class TestPolicyFiles:
    @pytest.mark.parametrize("name", ["kr_labor_pay_2026.yaml", "kr_labor_pay_2027.yaml"])
    def test_policy_validates(self, name):
        report = validate_policy((_POLICY_DIR / name).read_text(encoding="utf-8"), "payroll", "kr_labor_pay")
        assert report["status"] == "ok", report["findings"]


class TestWeeklyHolidayHours:
    def test_full_time_40_hours(self):
        # 40 / 5 = 8시간, 8 × 10,320 = 82,560
        r = call(weekly_contract_hours="40", hourly_ordinary_wage="10320", year=2026)
        assert r["eligible"] is True
        assert Decimal(r["holiday_hours"])      == Decimal("8")
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("82560")

    def test_part_time_20_hours_proportional(self):
        # 20 × 4 / (5 × 4) = 4시간, 4 × 10,320 = 41,280
        r = call(weekly_contract_hours="20", hourly_ordinary_wage="10320", year=2026)
        assert Decimal(r["holiday_hours"])      == Decimal("4")
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("41280")

    def test_fifteen_hours_is_eligible(self):
        # 15시간 미만만 제외하므로 15시간은 적용: 15 / 5 = 3시간
        r = call(weekly_contract_hours="15", hourly_ordinary_wage="10320", year=2026)
        assert r["eligible"] is True
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("30960")

    def test_just_below_fifteen_hours_is_excluded(self):
        r = call(weekly_contract_hours="14.99", hourly_ordinary_wage="10320", year=2026)
        assert r["eligible"] is False
        assert Decimal(r["holiday_hours"])      == Decimal("0")
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("0")
        assert any("제18조제3항" in reason for reason in r["ineligible_reasons"])

    def test_daily_hours_capped_at_eight(self):
        # 50 / 5 = 10시간이지만 제50조제2항 1일 8시간 상한
        r = call(weekly_contract_hours="50", hourly_ordinary_wage="10000", year=2026)
        assert Decimal(r["holiday_hours"])      == Decimal("8")
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("80000")

    def test_regular_worker_six_days(self):
        # 통상 근로자 주 6일: 30 / 6 = 5시간
        r = call(
            weekly_contract_hours="30", hourly_ordinary_wage="10000", year=2026,
            regular_worker_weekly_days=6,
        )
        assert Decimal(r["holiday_hours"]) == Decimal("5")
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("50000")

    def test_fraction_won_is_rounded_up(self):
        # 17 / 5 = 3.4시간, 3.4 × 10,321 = 35,091.4 -> 35,092
        r = call(weekly_contract_hours="17", hourly_ordinary_wage="10321", year=2026)
        assert Decimal(r["holiday_hours"])      == Decimal("3.4")
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("35092")


class TestEligibility:
    def test_absence_removes_allowance(self):
        r = call(weekly_contract_hours="40", hourly_ordinary_wage="10320", year=2026, perfect_attendance=False)
        assert r["eligible"] is False
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("0")
        assert any("제30조제1항" in reason for reason in r["ineligible_reasons"])

    def test_employment_ending_mid_week_removes_allowance(self):
        r = call(weekly_contract_hours="40", hourly_ordinary_wage="10320", year=2026, employed_through_week=False)
        assert r["eligible"] is False
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("0")

    def test_policy_fields(self):
        r = call(weekly_contract_hours="40", hourly_ordinary_wage="10320", year=2026)
        assert r["policy_version"]["year"] == 2026
        assert r["policy_status"] == "enacted"
        assert any(c["law"] == "근로기준법" for c in r["policy_citations"])

    def test_year_2027_uses_same_statutory_rule(self):
        # 2027년 최저시급 10,700원(고용노동부고시 제2026-60호) × 8시간 = 85,600
        r = call(weekly_contract_hours="40", hourly_ordinary_wage="10700", year=2027)
        assert Decimal(r["weekly_holiday_pay"]) == Decimal("85600")
        assert r["policy_effective_date"] == "2027-01-01"


class TestValidation:
    @pytest.mark.parametrize("hours", ["-1", "169", "NaN", "Infinity"])
    def test_bad_hours(self, hours):
        with pytest.raises(InvalidInputError):
            call(weekly_contract_hours=hours, hourly_ordinary_wage="10320", year=2026)

    def test_negative_wage(self):
        with pytest.raises(InvalidInputError):
            call(weekly_contract_hours="40", hourly_ordinary_wage="-1", year=2026)

    @pytest.mark.parametrize("days", [0, 8, True])
    def test_bad_regular_days(self, days):
        with pytest.raises(InvalidInputError):
            call(
                weekly_contract_hours="40", hourly_ordinary_wage="10320", year=2026,
                regular_worker_weekly_days=days,
            )

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(weekly_contract_hours="40", hourly_ordinary_wage="10320", year=2020)
