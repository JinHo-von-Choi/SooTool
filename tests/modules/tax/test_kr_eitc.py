"""tax.kr_eitc (근로장려금) 시험.

작성자: 최진호
작성일: 2026-10-03

기대값 출처:
  - 산정표 금액: 조세특례제한법 시행령 [별표 11] 근로장려금 산정표 (개정 2025.2.28., 대통령령 제35347호)
    https://www.law.go.kr/LSW/flDownload.do?gubun=&flSeq=170016365&bylClsCd=110201
  - 요건과 감액: 조세특례제한법 제100조의3, 제100조의5제3항·제4항, 제100조의7제2항·제3항
  - 총소득 구성(사업소득 총수입금액 x 업종별 조정률, 종교인소득 총수입금액)과 업종별 조정률:
    시행령 제100조의3제1항, 국세청 근로·자녀장려금 신청자격 안내
    https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?mi=2452&cntntsId=7783
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import TypeAdapter

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY
from sootool.modules.tax.kr_eitc import KrEitcResult
from sootool.policies import UnsupportedPolicyError
from sootool.policy_mgmt.loader import load as policy_load

_LOW_PROPERTY = "100000000"


def call(**kwargs):
    kwargs.setdefault("year", 2025)
    kwargs.setdefault("property_total", _LOW_PROPERTY)
    return REGISTRY.invoke("tax.kr_eitc", **kwargs)


def amount(**kwargs) -> Decimal:
    return Decimal(call(**kwargs)["eitc_amount"])


class TestCalculationTable:
    """별표 11 해당 구간 금액을 그대로 쓴다."""

    def test_single_phase_in(self):
        # 별표 11: 2,000,000 이상 2,100,000 미만, 단독 867,000
        r = call(household_type="single", earned_income="2050000")
        assert r["section"] == "phase_in"
        assert Decimal(r["table_amount"]) == Decimal("867000")
        assert Decimal(r["eitc_amount"]) == Decimal("867000")

    def test_single_plateau_is_max_amount(self):
        # 법 제100조의5제1항제1호나목: 400만원 이상 900만원 미만 165만원
        r = call(household_type="single", earned_income="8500000")
        assert r["section"] == "plateau"
        assert Decimal(r["eitc_amount"]) == Decimal("1650000")
        assert (r["table_bracket_lower"], r["table_bracket_upper"]) == ("8500000", "8600000")

    def test_single_phase_out(self):
        # 별표 11: 19,000,000 이상 19,100,000 미만, 단독 381,000
        assert amount(household_type="single", earned_income="19050000") == Decimal("381000")

    def test_one_earner_low_income_follows_table_not_formula(self):
        # 별표 11: 1,000,000 이상 1,100,000 미만, 홑벌이 454,000 (단독과 같은 금액)
        assert amount(household_type="one_earner", earned_income="1050000") == Decimal("454000")

    def test_one_earner_phase_in(self):
        # 별표 11: 4,000,000 이상 4,100,000 미만, 홑벌이 1,670,000
        assert amount(household_type="one_earner", earned_income="4050000") == Decimal("1670000")

    def test_one_earner_plateau(self):
        # 법 제100조의5제1항제2호나목: 700만원 이상 1,400만원 미만 285만원
        assert amount(household_type="one_earner", earned_income="10000000") == Decimal("2850000")

    def test_dual_earner_phase_in_combines_spouse(self):
        # 법 제100조의5제3항 합산 6,050,000. 별표 11: 6,000,000 이상 6,100,000 미만, 맞벌이 2,517,000
        r = call(household_type="dual_earner", earned_income="3000000", spouse_earned_income="3050000")
        assert r["total_earnings"] == "6050000"
        assert Decimal(r["eitc_amount"]) == Decimal("2517000")

    def test_dual_earner_plateau(self):
        # 법 제100조의5제1항제3호나목: 800만원 이상 1,700만원 미만 330만원
        assert amount(
            household_type="dual_earner", earned_income="6000000", spouse_earned_income="6000000",
        ) == Decimal("3300000")

    def test_dual_earner_phase_out_under_4400(self):
        # 2025.1.1. 이후 신청분 맞벌이 기준 4,400만원. 별표 11: 43,000,000 이상 43,100,000 미만 123,000
        assert amount(
            household_type="dual_earner", earned_income="22000000", spouse_earned_income="21050000",
        ) == Decimal("123000")


class TestMinimumAward:
    """법 제100조의7제3항 최소 지급 규칙."""

    def test_below_table_start_is_zero(self):
        # 별표 11 은 40,000원부터 시작한다
        r = call(household_type="single", earned_income="30000")
        assert Decimal(r["eitc_amount"]) == 0
        assert "table_bracket_lower" not in r

    def test_phase_in_floor_100000(self):
        # 별표 11 40,000~70,000 단독 29,000 -> 점증구간 1만5천원 이상 10만원 미만은 10만원
        r = call(household_type="single", earned_income="50000")
        assert Decimal(r["table_amount"]) == Decimal("29000")
        assert Decimal(r["eitc_amount"]) == Decimal("100000")
        assert r["minimum_rule"] == "phase_in_floor"

    def test_phase_out_floor_30000(self):
        # 별표 11 21,800,000~21,881,900 단독 26,000 -> 점감구간 3만원 미만은 3만원
        r = call(household_type="single", earned_income="21850000")
        assert Decimal(r["table_amount"]) == Decimal("26000")
        assert Decimal(r["eitc_amount"]) == Decimal("30000")
        assert r["minimum_rule"] == "phase_out_floor"

    def test_single_dash_bracket_is_zero(self):
        # 별표 11 21,881,900~21,900,000 단독 "-"
        assert amount(household_type="single", earned_income="21890000") == 0

    def test_dual_tail_sub_brackets(self):
        # 별표 11 43,754,600~43,800,000 맞벌이 30,000 / 43,800,000~43,877,300 25,000 / 43,877,300 이상 "-"
        assert amount(
            household_type="dual_earner", earned_income="22000000", spouse_earned_income="21760000",
        ) == Decimal("30000")
        r = call(household_type="dual_earner", earned_income="22000000", spouse_earned_income="21850000")
        assert Decimal(r["table_amount"]) == Decimal("25000")
        assert Decimal(r["eitc_amount"]) == Decimal("30000")
        assert amount(
            household_type="dual_earner", earned_income="22000000", spouse_earned_income="21880000",
        ) == 0


class TestReductions:
    def test_property_at_170m_halves(self):
        # 법 제100조의5제4항: 1억7천만원 이상이면 100분의 50. 1,650,000 x 0.5
        r = call(household_type="single", earned_income="8500000", property_total="170000000")
        assert r["property_reduced"] is True
        assert Decimal(r["eitc_amount"]) == Decimal("825000")

    def test_property_just_below_170m_not_reduced(self):
        r = call(household_type="single", earned_income="8500000", property_total="169999999")
        assert r["property_reduced"] is False
        assert Decimal(r["eitc_amount"]) == Decimal("1650000")

    def test_late_application_95_percent(self):
        # 법 제100조의7제2항: 1,650,000 x 0.95
        assert amount(household_type="single", earned_income="8500000", late_application=True) == Decimal("1567500")

    def test_property_and_late_combined(self):
        # 1,650,000 x 0.5 x 0.95
        assert amount(
            household_type="single", earned_income="8500000", property_total="200000000", late_application=True,
        ) == Decimal("783750")

    def test_reduced_phase_in_amount_raised_to_100000(self):
        # 별표 11 100,000~200,000 단독 83,000 x 0.5 = 41,500 -> 10만원
        assert amount(household_type="single", earned_income="150000", property_total="200000000") == Decimal("100000")

    def test_reduced_phase_out_amount_raised_to_30000(self):
        # 별표 11 21,600,000~21,700,000 단독 51,000 x 0.5 = 25,500 -> 3만원
        assert amount(household_type="single", earned_income="21650000", property_total="200000000") == Decimal("30000")

    def test_reduced_below_15000_is_zero(self):
        # 26,000 x 0.5 = 13,000 < 15,000 -> 없음
        r = call(household_type="single", earned_income="21850000", property_total="200000000")
        assert Decimal(r["reduced_amount"]) == Decimal("13000")
        assert Decimal(r["eitc_amount"]) == 0
        assert r["minimum_rule"] == "below_minimum"


class TestEligibility:
    def test_property_at_limit_is_ineligible(self):
        # 법 제100조의3제1항제4호: 2억4천만원 미만
        r = call(household_type="single", earned_income="8500000", property_total="240000000")
        assert r["eligible"] is False
        assert r["ineligible_reasons"] == ["property_not_below_limit"]
        assert Decimal(r["eitc_amount"]) == 0

    def test_total_income_at_limit_is_ineligible(self):
        # 법 제100조의3제1항제2호: 단독 2,200만원 미만. 근로 2,100만 + 이자 등 100만 = 2,200만
        r = call(household_type="single", earned_income="21000000", other_income="1000000")
        assert r["eligible"] is False
        assert r["ineligible_reasons"] == ["total_income_not_below_limit"]
        assert Decimal(r["eitc_amount"]) == 0

    def test_total_income_just_below_limit(self):
        # 총소득 21,999,999. 총급여액 등 21,000,000 -> 별표 11 단독 127,000
        r = call(household_type="single", earned_income="21000000", other_income="999999")
        assert r["eligible"] is True
        assert Decimal(r["eitc_amount"]) == Decimal("127000")


class TestIncomeConversion:
    def test_business_revenue_times_adjustment_rate(self):
        # 시행령 제100조의3제1항제4호나목 소매업 25%: 4,000만 x 0.25 = 1,000만
        # 별표 11 10,000,000~10,100,000 단독 1,524,000
        r = call(household_type="single", business_income=[{"industry": "retail", "revenue": "40000000"}])
        assert Decimal(r["total_earnings"]) == Decimal("10000000")
        assert Decimal(r["eitc_amount"]) == Decimal("1524000")
        assert r["business_lines"][0]["adjustment_rate"] == "0.25"

    def test_real_estate_rental_counts_in_total_income_only(self):
        # 차목 부동산임대업 90%: 1,000만 x 0.9 = 900만은 총소득에만 넣고 총급여액 등에서는 뺀다(시행령 제100조의6제2항제5호)
        r = call(
            household_type="single", earned_income="5000000",
            business_income=[{"industry": "real_estate_rental", "revenue": "10000000"}],
        )
        assert Decimal(r["total_earnings"]) == Decimal("5000000")
        assert Decimal(r["total_income"]) == Decimal("14000000")
        assert Decimal(r["eitc_amount"]) == Decimal("1650000")

    def test_real_estate_rental_can_break_income_limit(self):
        # 500만 + 2,000만 x 0.9 = 2,300만 >= 2,200만
        r = call(
            household_type="single", earned_income="5000000",
            business_income=[{"industry": "real_estate_rental", "revenue": "20000000"}],
        )
        assert r["eligible"] is False

    def test_religious_income_at_gross(self):
        # 종교인소득은 총수입금액 그대로. 500만원은 단독 평탄구간 165만원
        assert amount(household_type="single", religious_income="5000000") == Decimal("1650000")

    def test_spouse_business_income_in_dual_household(self):
        # 근로 2,000만 + 배우자 소매 4,000만 x 0.25 = 3,000만. 별표 11 맞벌이 1,712,000
        # 재산 1.8억(50%), 기한 후(95%): 1,712,000 x 0.5 x 0.95 = 813,200
        r = REGISTRY.invoke(
            "tax.kr_eitc", year=2026, household_type="dual_earner", property_total="180000000",
            earned_income="20000000", spouse_business_income=[{"industry": "retail", "revenue": "40000000"}],
            late_application=True,
        )
        assert Decimal(r["eitc_amount"]) == Decimal("813200")


class TestInvalidInput:
    def test_unknown_household_type(self):
        with pytest.raises(InvalidInputError):
            call(household_type="family", earned_income="1000000")

    def test_negative_amount(self):
        with pytest.raises(InvalidInputError):
            call(household_type="single", earned_income="-1")

    def test_unknown_industry(self):
        with pytest.raises(InvalidInputError):
            call(household_type="single", business_income=[{"industry": "space", "revenue": "1000"}])

    def test_malformed_business_item(self):
        with pytest.raises(InvalidInputError):
            call(household_type="single", business_income=[{"revenue": "1000"}])

    def test_single_with_spouse_income(self):
        with pytest.raises(InvalidInputError):
            call(household_type="single", earned_income="5000000", spouse_earned_income="1000000")

    def test_dual_requires_each_3m(self):
        # 법 제100조의3제5항제3호: 부부 각각 300만원 이상
        with pytest.raises(InvalidInputError):
            call(household_type="dual_earner", earned_income="10000000", spouse_earned_income="2999999")

    def test_one_earner_with_both_over_3m(self):
        with pytest.raises(InvalidInputError):
            call(household_type="one_earner", earned_income="10000000", spouse_earned_income="3000000")

    def test_one_earner_spouse_below_3m_is_combined(self):
        # 홑벌이 가목: 배우자 총급여액 등 300만원 미만. 합산 1,000만 + 200만 = 1,200만 -> 285만원
        assert amount(
            household_type="one_earner", earned_income="10000000", spouse_earned_income="2000000",
        ) == Decimal("2850000")


class TestPolicyVersions:
    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(year=2024, household_type="single", earned_income="5000000")

    def test_as_of_before_effective_date(self):
        with pytest.raises(PolicyNotInEffectError):
            call(household_type="single", earned_income="5000000", as_of="2024-12-31")

    def test_as_of_after_effective_date(self):
        r = call(household_type="single", earned_income="5000000", as_of="2025-01-01")
        assert r["policy_effective_date"] == "2025-01-01"

    def test_2026_uses_same_statutory_values(self):
        r = call(year=2026, household_type="dual_earner", earned_income="22000000", spouse_earned_income="21050000")
        assert Decimal(r["eitc_amount"]) == Decimal("123000")
        assert Decimal(r["total_income_limit"]) == Decimal("44000000")


class TestPolicyData:
    """산정표 자료의 구조 검사."""

    @pytest.mark.parametrize("year", [2025, 2026])
    def test_table_is_contiguous_and_bounded(self, year):
        data  = policy_load("tax", "kr_eitc", year)["data"]
        table = data["calculation_table"]
        assert table[0][0] == 40000
        assert table[-1][1] == 44000000
        for prev, cur in zip(table, table[1:], strict=False):
            assert prev[1] == cur[0]
        maxima = [data["household_types"][k]["max_amount"] for k in ("single", "one_earner", "dual_earner")]
        for row in table:
            assert row[0] < row[1]
            for value, cap in zip(row[2:], maxima, strict=True):
                assert value is None or 0 < value <= cap

    def test_dual_column_starts_at_combined_6m(self):
        # 맞벌이는 부부 각각 300만원 이상이라 합산 600만원 미만 구간은 해당 없음
        table = policy_load("tax", "kr_eitc", 2025)["data"]["calculation_table"]
        assert all(row[4] is None for row in table if row[1] <= 6000000)
        assert all(row[4] is not None for row in table if 6000000 <= row[0] < 43877300)


def test_result_matches_declared_type():
    r = call(
        household_type="dual_earner", earned_income="5000000",
        spouse_business_income=[{"industry": "manufacturing", "revenue": "10000000"}],
    )
    TypeAdapter(KrEitcResult).validate_python(r)
