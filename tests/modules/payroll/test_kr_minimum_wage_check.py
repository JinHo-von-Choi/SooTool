"""Tests for payroll.kr_minimum_wage_check.

Author: 최진호
Date: 2026-10-03

기대값 출처:
  2026년 적용 최저임금 고시(고용노동부고시 제2025-47호): 시간급 10,320원, 월 환산액 2,156,880원(209시간)
  2027년 적용 최저임금 고시(고용노동부고시 제2026-60호): 시간급 10,700원, 월 환산액 2,236,300원(209시간)
  최저임금법 제5조제2항·시행령 제3조: 수습 감액 100분의 10
  최저임금법 제6조제4항, 부칙 <법률 제15666호> 제2조: 2024년부터 상여금·현금 복리후생비 산입 제외 비율 0
  최저임금법 시행령 제5조제1항: 일급 / 1일 소정근로시간, 월급 / (주 소정 + 주휴) × 365 / 7 / 12
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

_POLICY_DIR = Path(__file__).resolve().parents[3] / "src" / "sootool" / "policies" / "payroll"


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_minimum_wage_check", **kwargs)


class TestPolicyFiles:
    @pytest.mark.parametrize("name", ["kr_minimum_wage_2026.yaml", "kr_minimum_wage_2027.yaml"])
    def test_policy_validates(self, name):
        report = validate_policy((_POLICY_DIR / name).read_text(encoding="utf-8"), "payroll", "kr_minimum_wage")
        assert report["status"] == "ok", report["findings"]


class TestNoticeValues:
    def test_2026_monthly_at_minimum_is_compliant(self):
        r = call(wage_amount="2156880", year=2026)
        assert r["statutory_hourly_minimum"] == "10320"
        assert r["monthly_standard_hours"]   == "209"
        assert r["notice_monthly_amount"]    == "2156880"
        assert r["minimum_monthly_amount"]   == "2156880"
        assert r["compliant"] is True
        assert r["monthly_shortfall"]        == "0"

    def test_2026_one_won_short(self):
        r = call(wage_amount="2156879", year=2026)
        assert r["compliant"] is False
        assert r["monthly_shortfall"] == "1"

    def test_2027_notice(self):
        # 2,236,300 - 2,156,880 = 79,420
        r = call(wage_amount="2156880", year=2027)
        assert r["statutory_hourly_minimum"] == "10700"
        assert r["minimum_monthly_amount"]   == "2236300"
        assert r["notice_monthly_amount"]    == "2236300"
        assert r["compliant"] is False
        assert r["monthly_shortfall"]        == "79420"

    def test_2027_not_in_effect_before_start(self):
        with pytest.raises(PolicyNotInEffectError):
            call(wage_amount="2236300", year=2027, as_of="2026-12-31")

    def test_2027_in_effect_on_start(self):
        r = call(wage_amount="2236300", year=2027, as_of="2027-01-01")
        assert r["compliant"] is True
        assert r["policy_effective_date"] == "2027-01-01"

    def test_2026_not_in_effect_after_period(self):
        with pytest.raises(PolicyNotInEffectError):
            call(wage_amount="2156880", year=2026, as_of="2027-01-01")


class TestUnits:
    def test_hourly(self):
        assert call(wage_amount="10320", wage_unit="hourly", year=2026)["compliant"] is True
        r = call(wage_amount="10319", wage_unit="hourly", year=2026)
        assert r["compliant"] is False
        assert r["hourly_shortfall"] == "1.00"

    def test_daily(self):
        # 82,560 / 8 = 10,320
        r = call(wage_amount="82560", wage_unit="daily", daily_contract_hours="8", year=2026)
        assert r["compliant"] is True

    def test_weekly(self):
        # 495,360 / (40 + 8) = 10,320
        r = call(wage_amount="495360", wage_unit="weekly", year=2026)
        assert r["compliant"] is True

    def test_part_time_monthly(self):
        # 주 20시간: 주휴 4시간, 24 × 365 / 7 / 12 = 104.29 -> 104시간, 10,320 × 104 = 1,073,280
        r = call(wage_amount="1073280", weekly_contract_hours="20", year=2026)
        assert r["monthly_standard_hours"] == "104"
        assert r["minimum_monthly_amount"] == "1073280"
        assert r["compliant"] is True
        assert call(wage_amount="1073279", weekly_contract_hours="20", year=2026)["compliant"] is False


class TestInclusion:
    def test_monthly_bonus_fully_included_since_2024(self):
        r = call(wage_amount="2000000", monthly_bonus="156880", year=2026)
        assert r["inclusion"]["bonus_included"] == "156880"
        assert r["inclusion"]["bonus_excluded"] == "0"
        assert r["compliant"] is True

    def test_monthly_welfare_cash_fully_included_since_2024(self):
        r = call(wage_amount="1956880", monthly_welfare_cash="200000", year=2026)
        assert r["inclusion"]["welfare_cash_excluded"] == "0"
        assert r["compliant"] is True

    def test_hourly_worker_with_monthly_bonus(self):
        # 시급 10,000 + 월 상여 66,880 / 209 = 320 -> 10,320
        r = call(wage_amount="10000", wage_unit="hourly", monthly_bonus="66880", year=2026)
        assert r["compliant"] is True


class TestProbation:
    def test_reduction_when_all_conditions_met(self):
        # 10,320 × 0.9 = 9,288
        r = call(
            wage_amount="9288", wage_unit="hourly", year=2026,
            on_probation=True, contract_one_year_or_more=True,
        )
        assert r["probation_reduction_applied"] is True
        assert Decimal(r["applicable_hourly_minimum"]) == Decimal("9288")
        assert r["compliant"] is True

    def test_simple_labor_job_excluded(self):
        r = call(
            wage_amount="9288", wage_unit="hourly", year=2026,
            on_probation=True, contract_one_year_or_more=True, simple_labor_job=True,
        )
        assert r["probation_reduction_applied"] is False
        assert r["compliant"] is False

    def test_short_contract_excluded(self):
        r = call(wage_amount="9288", wage_unit="hourly", year=2026, on_probation=True)
        assert r["probation_reduction_applied"] is False
        assert r["compliant"] is False


class TestValidation:
    def test_bad_unit(self):
        with pytest.raises(InvalidInputError):
            call(wage_amount="2156880", wage_unit="annual", year=2026)

    @pytest.mark.parametrize("field", ["wage_amount", "monthly_bonus", "monthly_welfare_cash"])
    def test_negative_amount(self, field):
        kwargs = {"wage_amount": "2156880", "year": 2026, field: "-1"}
        with pytest.raises(InvalidInputError):
            call(**kwargs)

    def test_daily_requires_hours(self):
        with pytest.raises(InvalidInputError):
            call(wage_amount="82560", wage_unit="daily", year=2026)

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(wage_amount="2156880", year=2025)
