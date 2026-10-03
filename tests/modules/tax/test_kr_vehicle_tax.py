"""Tests for tax.kr_vehicle_tax (승용자동차 자동차세).

기대값은 지방세법 제127조제1항, 제128조제3항, 제151조제1항제7호와 같은 법 시행령 제122조제2항,
제125조제6항(이자율 5%)을 조문대로 손으로 계산한 값이다. 끝수는 10원 미만 버림
(지방세기본법 제59조, 국고금 관리법 제47조).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_vehicle_tax", **kwargs)


def money(result, key):
    return Decimal(result[key])


class TestCcRates:
    """비영업용 시시당 세액 80/140/200원, 구간 세율을 배기량 전체에 적용 (제127조제1항제1호)."""

    @pytest.mark.parametrize("cc, annual", [
        (1000, 80000),     # 1,000cc x 80
        (1001, 140140),    # 1,001cc x 140
        (1600, 224000),    # 1,600cc x 140
        (1601, 320200),    # 1,601cc x 200
    ])
    def test_bracket_boundaries(self, cc, annual):
        # 차령기산일 2025-05-01 -> 2026년 차령 2년, 경감 없음
        r = call(year=2026, displacement_cc=cc, age_start_date="2025-05-01")
        assert money(r, "base_annual_tax") == annual
        assert money(r, "annual_vehicle_tax") == annual

    def test_business_rates_and_truncation(self):
        """영업용 2,501cc x 24원 = 60,024, 기분 30,012 -> 30,010 (10원 미만 버림), 지방교육세 없음."""
        r = call(year=2026, displacement_cc=2501, business_use=True)
        assert money(r, "per_cc_rate") == 24
        assert money(r, "first_half_tax") == 30010
        assert money(r, "annual_vehicle_tax") == 60020
        assert r["local_education_tax_applies"] is False
        assert money(r, "local_education_tax") == 0
        assert money(r, "total_payable") == 60020

    def test_business_2000cc_is_19_won(self):
        r = call(year=2026, displacement_cc=2000, business_use=True)
        assert money(r, "annual_vehicle_tax") == 38000


class TestVehicleAgeReduction:
    def test_age_six_reduces_twenty_percent(self):
        """1,998cc, 기산일 2021-03-10: 차령 6. 기분세액 199,800 - 199,800 x 5% x 4 = 159,840.
        지방교육세 기분마다 47,952 -> 47,950."""
        r = call(year=2026, displacement_cc=1998, age_start_date="2021-03-10")
        assert r["vehicle_age_first_half"] == 6
        assert money(r, "first_half_tax") == 159840
        assert money(r, "second_half_tax") == 159840
        assert money(r, "annual_vehicle_tax") == 319680
        assert money(r, "local_education_tax") == 95900
        assert money(r, "total_payable") == 415580

    def test_age_two_has_no_reduction(self):
        r = call(year=2026, displacement_cc=1998, age_start_date="2025-01-02")
        assert r["vehicle_age_second_half"] == 2
        assert money(r, "annual_vehicle_tax") == 399600

    def test_age_over_twelve_is_capped_at_fifty_percent(self):
        """기산일 2010-01-01 -> 차령 17, 12년으로 보아 (12 - 2) x 5% = 50% 경감."""
        r = call(year=2026, displacement_cc=1998, age_start_date="2010-01-01")
        assert money(r, "annual_vehicle_tax") == 199800

    def test_second_half_start_date_splits_age(self):
        """기산일 2023-08-15: 제1기분 차령 3(5% 경감), 제2기분 차령 4(10% 경감) (시행령 제122조제2항제2호).
        199,800 - 9,990 = 189,810, 199,800 - 19,980 = 179,820."""
        r = call(year=2026, displacement_cc=1998, age_start_date="2023-08-15")
        assert (r["vehicle_age_first_half"], r["vehicle_age_second_half"]) == (3, 4)
        assert money(r, "first_half_tax") == 189810
        assert money(r, "second_half_tax") == 179820
        assert money(r, "annual_vehicle_tax") == 369630


class TestAnnualPayment:
    """1,998cc, 차령 6, 연세액 319,680원, 제2기분 159,840원."""

    base = {"year": 2026, "displacement_cc": 1998, "age_start_date": "2021-03-10"}

    def test_january(self):
        """319,680 x 334/365 x 5% = 14,626.3... -> 납부 305,053.7 -> 305,050. 교육세 91,515 -> 91,510."""
        r = call(**self.base, annual_payment="january")
        assert money(r, "vehicle_tax_payable") == 305050
        assert money(r, "annual_payment_deduction") == 14630
        assert money(r, "local_education_tax") == 91510
        assert money(r, "total_payable") == 396560

    def test_march(self):
        """319,680 x 275/365 x 5% = 12,042.7... -> 납부 307,637.2 -> 307,630."""
        r = call(**self.base, annual_payment="march")
        assert money(r, "vehicle_tax_payable") == 307630

    def test_june(self):
        """제2기분 159,840 x 5% = 7,992 -> 납부 311,688 -> 311,680. 교육세 93,504 -> 93,500."""
        r = call(**self.base, annual_payment="june")
        assert money(r, "vehicle_tax_payable") == 311680
        assert money(r, "local_education_tax") == 93500

    def test_september(self):
        """159,840 x 92/184 x 5% = 3,996 -> 납부 315,684 -> 315,680."""
        r = call(**self.base, annual_payment="september")
        assert money(r, "vehicle_tax_payable") == 315680


class TestOtherPassenger:
    def test_electric_non_business(self):
        """그 밖의 승용 비영업용 100,000원, 지방교육세 30% (제127조제1항제3호, 제150조제7호)."""
        r = call(year=2026, vehicle_type="other_passenger")
        assert money(r, "annual_vehicle_tax") == 100000
        assert money(r, "local_education_tax") == 30000
        assert money(r, "total_payable") == 130000

    def test_electric_business(self):
        r = call(year=2026, vehicle_type="other_passenger", business_use=True)
        assert money(r, "annual_vehicle_tax") == 20000
        assert money(r, "local_education_tax") == 0


class TestErrorsAndPolicy:
    @pytest.mark.parametrize("kwargs", [
        {"displacement_cc": None, "age_start_date": "2021-01-01"},
        {"displacement_cc": 0, "age_start_date": "2021-01-01"},
        {"displacement_cc": True, "age_start_date": "2021-01-01"},
        {"displacement_cc": 1998},
        {"displacement_cc": 1998, "age_start_date": "2021/01/01"},
        {"displacement_cc": 1998, "age_start_date": "2027-01-01"},
        {"displacement_cc": 1998, "age_start_date": "2021-01-01", "annual_payment": "december"},
        {"vehicle_type": "truck"},
    ])
    def test_invalid_inputs(self, kwargs):
        with pytest.raises(InvalidInputError):
            call(year=2026, **kwargs)

    def test_as_of_before_effective_date(self):
        with pytest.raises(PolicyNotInEffectError):
            call(year=2026, vehicle_type="other_passenger", as_of="2025-12-31")

    def test_as_of_within_effective_period(self):
        r = call(year=2026, vehicle_type="other_passenger", as_of="2026-06-01")
        assert r["policy_effective_date"] == "2026-01-01"
        assert any(c["article"] == "제125조제6항" for c in r["policy_citations"])
