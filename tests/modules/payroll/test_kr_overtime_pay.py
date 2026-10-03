"""Tests for payroll.kr_overtime_pay.

Author: 최진호
Date: 2026-10-03

기대값은 근로기준법 제56조(연장 50%, 휴일 8시간 이내 50%·초과 100%, 야간 50% 가산), 제11조제2항과 시행령 제7조
별표 1(상시 4명 이하 사업장 제56조 미적용), 시행령 제6조제2항(시간급 통상임금 환산)과 2026년 적용 최저임금 고시
(고용노동부고시 제2025-47호)의 월 환산 기준시간 209시간(주 40시간 + 주휴 8시간)으로 직접 계산했다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    kwargs.setdefault("year", 2026)
    kwargs.setdefault("employee_count", 10)
    return REGISTRY.invoke("payroll.kr_overtime_pay", **kwargs)


class TestPremiumRates:
    def test_overtime_150_percent(self):
        # 2시간 × 10,000 = 20,000 + 가산 50% 10,000
        r = call(ordinary_wage="10000", overtime_hours="2")
        assert Decimal(r["base_pay"])              == Decimal("20000")
        assert Decimal(r["premiums"]["overtime"])  == Decimal("10000")
        assert Decimal(r["total_pay"])             == Decimal("30000")

    def test_overtime_at_night_200_percent(self):
        # 연장 2시간이 모두 22시 이후: 100% + 연장 50% + 야간 50%
        r = call(ordinary_wage="10000", overtime_hours="2", night_hours="2")
        assert Decimal(r["premiums"]["night"]) == Decimal("10000")
        assert Decimal(r["total_pay"])         == Decimal("40000")

    def test_night_within_contract_hours_premium_only(self):
        # 소정근로시간 중 야간 3시간: 기본분은 소정임금에 포함, 가산 50%만
        r = call(ordinary_wage="10000", night_hours="3")
        assert Decimal(r["base_pay"])  == Decimal("0")
        assert Decimal(r["total_pay"]) == Decimal("15000")

    def test_holiday_ten_hours_one_day(self):
        # 100,000 + 8 × 5,000 + 2 × 10,000
        r = call(ordinary_wage="10000", holiday_hours_by_day=["10"])
        assert r["hours"]["holiday_within_limit"]            == "8"
        assert r["hours"]["holiday_over_limit"]              == "2"
        assert Decimal(r["premiums"]["holiday_within_limit"]) == Decimal("40000")
        assert Decimal(r["premiums"]["holiday_over_limit"])   == Decimal("20000")
        assert Decimal(r["total_pay"])                        == Decimal("160000")

    def test_holiday_limit_applies_per_day(self):
        # 휴일 이틀 각 8시간: 모두 8시간 이내 50%. 160,000 + 80,000
        r = call(ordinary_wage="10000", holiday_hours_by_day=["8", "8"])
        assert r["hours"]["holiday_over_limit"] == "0"
        assert Decimal(r["total_pay"])          == Decimal("240000")

    def test_holiday_over_eight_at_night_250_percent(self):
        # 휴일 10시간 중 초과 2시간이 야간: 그 2시간은 100% + 100% + 50%
        r = call(ordinary_wage="10000", holiday_hours_by_day=["10"], night_hours="2")
        assert Decimal(r["total_pay"]) == Decimal("170000")


class TestSmallWorkplace:
    def test_four_employees_no_premium(self):
        # 상시 4명 이하: 제56조 미적용. 근로시간분 (2 + 10) × 10,000 만 지급
        r = call(
            ordinary_wage="10000", employee_count=4,
            overtime_hours="2", night_hours="2", holiday_hours_by_day=["10"],
        )
        assert r["premium_applies"] is False
        assert Decimal(r["premium_total"]) == Decimal("0")
        assert Decimal(r["total_pay"])     == Decimal("120000")

    def test_five_employees_premium(self):
        r = call(ordinary_wage="10000", employee_count=5, overtime_hours="1")
        assert r["premium_applies"] is True
        assert Decimal(r["total_pay"]) == Decimal("15000")


class TestOrdinaryHourlyWage:
    def test_monthly_salary_209_hours(self):
        # 2,090,000 / 209 = 10,000. 연장 10시간 × 15,000
        r = call(ordinary_wage="2090000", wage_unit="monthly", overtime_hours="10")
        assert r["monthly_standard_hours"]          == "209"
        assert Decimal(r["hourly_ordinary_wage"])   == Decimal("10000.00")
        assert Decimal(r["total_pay"])              == Decimal("150000")

    def test_monthly_salary_3m(self):
        # 3,000,000 / 209 = 14,354.0669...; 연장 1시간 기본분 올림 14,355, 가산 7,177.03 -> 7,178
        r = call(ordinary_wage="3000000", wage_unit="monthly", overtime_hours="1")
        assert r["hourly_ordinary_wage"]          == "14354.07"
        assert Decimal(r["base_pay"])             == Decimal("14355")
        assert Decimal(r["premiums"]["overtime"]) == Decimal("7178")

    def test_monthly_salary_209_hours_no_spurious_rounding(self):
        # 3,000,000 / 209 × 209 = 3,000,000 정확히. 정밀도 끝자리 때문에 1원 올라가지 않아야 한다
        r = call(ordinary_wage="3000000", wage_unit="monthly", overtime_hours="209")
        assert Decimal(r["base_pay"]) == Decimal("3000000")

    def test_part_time_monthly_hours(self):
        # 주 30시간: 주휴 6시간, (30 + 6) × 365 / 7 / 12 = 156.43 -> 156시간
        r = call(ordinary_wage="1560000", wage_unit="monthly", weekly_contract_hours="30", overtime_hours="1")
        assert r["weekly_basis_hours"]     == "36"
        assert r["monthly_standard_hours"] == "156"
        assert Decimal(r["total_pay"])     == Decimal("15000")

    def test_monthly_hours_override(self):
        r = call(ordinary_wage="2085700", wage_unit="monthly", monthly_standard_hours="208.57", overtime_hours="1")
        assert Decimal(r["hourly_ordinary_wage"]) == Decimal("10000.00")

    def test_weekly_salary(self):
        # 480,000 / (40 + 8) = 10,000
        r = call(ordinary_wage="480000", wage_unit="weekly", overtime_hours="1")
        assert Decimal(r["total_pay"]) == Decimal("15000")

    def test_daily_wage(self):
        # 80,000 / 8 = 10,000
        r = call(ordinary_wage="80000", wage_unit="daily", daily_contract_hours="8", overtime_hours="1")
        assert Decimal(r["total_pay"]) == Decimal("15000")

    def test_fraction_won_rounded_up(self):
        # 10,001.5 × 0.5 = 5,000.75 -> 5,001
        r = call(ordinary_wage="10001.5", overtime_hours="1")
        assert Decimal(r["premiums"]["overtime"]) == Decimal("5001")
        assert Decimal(r["base_pay"])             == Decimal("10002")


class TestValidation:
    def test_daily_requires_daily_hours(self):
        with pytest.raises(InvalidInputError):
            call(ordinary_wage="80000", wage_unit="daily", overtime_hours="1")

    @pytest.mark.parametrize("unit", ["yearly", ""])
    def test_bad_unit(self, unit):
        with pytest.raises(InvalidInputError):
            call(ordinary_wage="10000", wage_unit=unit)

    @pytest.mark.parametrize("count", [0, -1, True])
    def test_bad_employee_count(self, count):
        with pytest.raises(InvalidInputError):
            call(ordinary_wage="10000", employee_count=count)

    @pytest.mark.parametrize("field", ["overtime_hours", "night_hours"])
    def test_negative_hours(self, field):
        with pytest.raises(InvalidInputError):
            call(ordinary_wage="10000", **{field: "-1"})

    def test_holiday_day_over_24(self):
        with pytest.raises(InvalidInputError):
            call(ordinary_wage="10000", holiday_hours_by_day=["25"])

    def test_zero_wage(self):
        with pytest.raises(InvalidInputError):
            call(ordinary_wage="0")

    def test_policy_fields(self):
        r = call(ordinary_wage="10000", overtime_hours="1")
        assert r["trace"]["tool"] == "payroll.kr_overtime_pay"
        assert r["policy_status"] == "enacted"
        assert any("제56조" in c.get("article", "") for c in r["policy_citations"])
