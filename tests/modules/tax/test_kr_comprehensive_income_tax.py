"""Tests for tax.kr_comprehensive_income_tax (종합소득세 신고 흐름).

기대값은 소득세법(법률 제21548호, 2026-04-21 시행본) 제14조제3항제6호·제8호가목, 제17조제3항, 제15조제2호,
제47조, 제47조의2, 제50조, 제51조, 제55조, 제56조, 제59조, 제59조의2, 제59조의4제9항, 제62조와
같은 법 시행령 제87조제1호의2, 제116조의2, 제119조의3제1항을 조문대로 손으로 계산한 값이다(원 미만 버림).
금융소득 비교과세 구성은 한국공인회계사회 사이버연수 「배당세액공제」 예시(이자 3천만원, 배당가산 대상
배당 1천만원, 비대상 배당 2천만원, 사업소득 5천만원, 종합소득공제 1천만원)를 2026년 세율과 배당가산율
10%로 다시 계산했다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    kwargs.setdefault("year", 2026)
    return REGISTRY.invoke("tax.kr_comprehensive_income_tax", **kwargs)


def dec(value) -> Decimal:
    return Decimal(str(value))


class TestWageOnly:
    def test_salary_50m_single(self):
        """총급여 5천만원, 본인 1명, 표준세액공제.

        근로소득공제 = 350만 + 400만 + 3천만 x 15% + 500만 x 5% = 12,250,000 (제47조)
        과세표준 = 37,750,000 - 1,500,000 = 36,250,000
        산출세액 = 840,000 + 22,250,000 x 15% = 4,177,500 (제55조)
        근로소득세액공제 = min(715,000 + 2,877,500 x 30% = 1,578,250, 한도 max(604,000, 660,000)) = 660,000 (제59조)
        결정세액 = 4,177,500 - 660,000 - 130,000 = 3,387,500, 지방소득세 338,750
        """
        r = call(total_salary="50000000", apply_standard_tax_credit=True)
        assert dec(r["labor_income_deduction"]) == Decimal("12250000")
        assert dec(r["taxable_income"]) == Decimal("36250000")
        assert dec(r["computed_tax"]) == Decimal("4177500")
        assert dec(r["labor_income_tax_credit"]) == Decimal("660000")
        assert dec(r["standard_tax_credit"]) == Decimal("130000")
        assert dec(r["decided_tax"]) == Decimal("3387500")
        assert dec(r["local_income_tax"]) == Decimal("338750")
        assert dec(r["total_tax"]) == Decimal("3726250")
        assert "financial_comparison" not in r

    def test_labor_credit_uses_labor_share_of_computed_tax(self):
        """총급여 2천만원과 사업소득 3천만원.

        근로소득공제 8,250,000, 근로소득금액 11,750,000, 종합소득금액 41,750,000, 과세표준 40,250,000
        산출세액 = 840,000 + 26,250,000 x 15% = 4,777,500
        근로소득분 산출세액 = 4,777,500 x 11,750,000 / 41,750,000 = 1,344,565 (시행령 제119조의3제1항, 원 미만 버림)
        근로소득세액공제 = 715,000 + 44,565 x 30% = 728,369 (한도 740,000 이내)
        """
        r = call(total_salary="20000000", business_income="30000000")
        assert dec(r["labor_income_amount"]) == Decimal("11750000")
        assert dec(r["comprehensive_income"]) == Decimal("41750000")
        assert dec(r["computed_tax"]) == Decimal("4777500")
        assert dec(r["labor_income_tax_credit"]) == Decimal("728369")
        assert dec(r["decided_tax"]) == Decimal("4049131")


class TestFinancialIncome:
    def test_kicpa_example_restated_for_2026(self):
        """이자 3천만, 배당가산 대상 1천만, 비대상 2천만, 사업소득 5천만, 종합소득공제 1천만원.

        기준금액은 이자 2천만원으로 채워져 배당가산 대상 1천만원 전액이 초과분이다(시행령 제116조의2).
        배당가산액 = 1,000,000, 종합소득금액 = 111,000,000, 과세표준 = 101,000,000
        제62조제1호 = 840,000 + 5,400,000 + 31,000,000 x 24% + 2,800,000 = 16,480,000
        제62조제2호 = 60,000,000 x 14% + 840,000 + 26,000,000 x 15% = 13,140,000
        배당세액공제 = min(1,000,000, 16,480,000 - 13,140,000) = 1,000,000
        """
        r = call(
            interest_income="30000000", dividend_gross_up_eligible="10000000", dividend_other="20000000",
            business_income="50000000", other_income_deductions="8500000",
        )
        assert r["financial_income_aggregated"] is True
        assert dec(r["dividend_gross_up"]) == Decimal("1000000")
        assert dec(r["comprehensive_income"]) == Decimal("111000000")
        assert dec(r["taxable_income"]) == Decimal("101000000")
        assert dec(r["financial_comparison"]["aggregated_method_tax"]) == Decimal("16480000")
        assert dec(r["financial_comparison"]["separate_method_tax"]) == Decimal("13140000")
        assert r["financial_comparison"]["applied"] == "aggregated"
        assert dec(r["computed_tax"]) == Decimal("16480000")
        assert dec(r["dividend_tax_credit"]) == Decimal("1000000")
        assert dec(r["decided_tax"]) == Decimal("15480000")

    def test_separate_method_wins_for_interest_only(self):
        """이자 3천만원만 있고 본인공제뿐: 제1호 8,500,000 x 6% + 2,800,000 = 3,310,000,
        제2호 30,000,000 x 14% = 4,200,000 → 산출세액 4,200,000. 표준세액공제 7만원(제59조의4제9항제2호나목)."""
        r = call(interest_income="30000000", apply_standard_tax_credit=True)
        assert dec(r["financial_comparison"]["aggregated_method_tax"]) == Decimal("3310000")
        assert dec(r["financial_comparison"]["separate_method_tax"]) == Decimal("4200000")
        assert r["financial_comparison"]["applied"] == "separate"
        assert dec(r["computed_tax"]) == Decimal("4200000")
        assert dec(r["standard_tax_credit"]) == Decimal("70000")
        assert dec(r["decided_tax"]) == Decimal("4130000")

    def test_dividend_credit_limited_by_comparison(self):
        """배당가산 대상 3천만원과 사업소득 2천만원.

        배당가산액 = 1천만원 x 10% = 1,000,000, 과세표준 49,500,000
        제1호 = 840,000 + 15,500,000 x 15% + 2,800,000 = 5,965,000
        제2호 = 4,200,000 + 840,000 + 4,500,000 x 15% = 5,715,000
        배당세액공제 = min(1,000,000, 250,000) = 250,000 (제15조제2호)
        """
        r = call(dividend_gross_up_eligible="30000000", business_income="20000000")
        assert dec(r["dividend_gross_up"]) == Decimal("1000000")
        assert dec(r["computed_tax"]) == Decimal("5965000")
        assert dec(r["financial_comparison"]["separate_method_tax"]) == Decimal("5715000")
        assert dec(r["dividend_tax_credit"]) == Decimal("250000")
        assert dec(r["decided_tax"]) == Decimal("5715000")

    def test_gross_up_only_on_excess_portion(self):
        """배당가산 대상 배당 2,500만원만 있으면 기준금액 초과 500만원에만 10% 가산(제56조제4항, 국심2007중1921)."""
        r = call(dividend_gross_up_eligible="25000000")
        assert dec(r["dividend_gross_up"]) == Decimal("500000")
        assert dec(r["financial_income_amount"]) == Decimal("25500000")

    def test_ordering_interest_and_other_dividend_fill_threshold_first(self):
        """이자 1,500만 + 비대상 배당 500만이 기준금액을 채우고 배당가산 대상 1천만원 전부가 초과분."""
        r = call(interest_income="15000000", dividend_other="5000000", dividend_gross_up_eligible="10000000")
        assert dec(r["dividend_gross_up"]) == Decimal("1000000")

    @pytest.mark.parametrize(("interest", "aggregated", "separate_tax"), [
        ("20000000", False, "2800000"),   # 2천만원 이하: 14% 분리과세
        ("20000001", True,  "0"),         # 초과: 종합과세
    ])
    def test_threshold_boundary(self, interest, aggregated, separate_tax):
        r = call(interest_income=interest)
        assert r["financial_income_aggregated"] is aggregated
        assert dec(r["financial_income_separate_tax"]) == Decimal(separate_tax)

    def test_separately_taxed_financial_income_is_not_in_comprehensive_income(self):
        r = call(interest_income="10000000", dividend_gross_up_eligible="10000000")
        assert dec(r["comprehensive_income"]) == Decimal("0")
        assert dec(r["dividend_gross_up"]) == Decimal("0")
        assert dec(r["computed_tax"]) == Decimal("0")


class TestPensionAndOtherIncome:
    def test_pension_income_deduction(self):
        """총연금액 1천만원: 490만 + 300만 x 20% = 5,500,000 (제47조의2), 연금소득금액 4,500,000."""
        r = call(pension_gross="10000000")
        assert dec(r["pension_income_deduction"]) == Decimal("5500000")
        assert dec(r["pension_income_amount"]) == Decimal("4500000")

    def test_other_income_three_million_is_separate(self):
        """의제경비 대상 750만원: 기타소득금액 300만원 이하 → 분리과세 20% = 600,000."""
        r = call(other_income_deemed_revenue="7500000")
        assert dec(r["other_income_total"]) == Decimal("3000000")
        assert r["other_income_aggregated"] is False
        assert dec(r["other_income_separate_tax"]) == Decimal("600000")
        assert dec(r["comprehensive_income"]) == Decimal("0")

    def test_other_income_over_three_million_is_aggregated(self):
        """7,500,010원: 의제경비 4,500,006, 기타소득금액 3,000,004 → 종합과세."""
        r = call(other_income_deemed_revenue="7500010")
        assert dec(r["other_income_total"]) == Decimal("3000004")
        assert r["other_income_aggregated"] is True
        assert dec(r["comprehensive_income"]) == Decimal("3000004")

    def test_other_income_aggregate_election(self):
        r = call(other_income_deemed_revenue="5000000", other_income_aggregate=True)
        assert r["other_income_aggregated"] is True
        assert dec(r["comprehensive_income"]) == Decimal("2000000")
        assert dec(r["other_income_separate_tax"]) == Decimal("0")

    def test_actual_expenses_above_sixty_percent(self):
        """실제 필요경비 700만원이 60%(600만원)보다 크면 실제 경비를 쓴다(시행령 제87조제1호의2 단서)."""
        r = call(other_income_deemed_revenue="10000000", other_income_actual_expenses="7000000")
        assert dec(r["other_income_total"]) == Decimal("3000000")


class TestDeductionsAndCredits:
    @pytest.mark.parametrize(("business", "additional"), [
        ("30000000", "500000"),   # 종합소득금액 3천만원 이하: 부녀자공제 50만원
        ("30000001", "0"),        # 초과: 미적용
    ])
    def test_woman_deduction_income_limit(self, business, additional):
        r = call(business_income=business, woman_deduction=True)
        assert dec(r["additional_deduction"]) == Decimal(additional)

    def test_single_parent_takes_precedence_over_woman(self):
        """제51조제1항 단서: 부녀자와 한부모에 모두 해당하면 한부모 100만원만."""
        r = call(business_income="20000000", dependents=2, woman_deduction=True, single_parent=True)
        assert dec(r["additional_deduction"]) == Decimal("1000000")

    def test_elderly_and_disabled(self):
        """70세 이상 1명 100만원 + 장애인 1명 200만원, 기본공제 3명 450만원."""
        r = call(business_income="50000000", dependents=3, elderly_count=1, disabled_count=1)
        assert dec(r["basic_deduction"]) == Decimal("4500000")
        assert dec(r["additional_deduction"]) == Decimal("3000000")
        assert dec(r["personal_deduction"]) == Decimal("7500000")

    def test_personal_deduction_capped_at_comprehensive_income(self):
        """총연금액 400만원: 공제 370만원, 연금소득금액 30만원. 기본공제 300만원은 30만원까지만(제51조제4항)."""
        r = call(pension_gross="4000000", dependents=2)
        assert dec(r["pension_income_amount"]) == Decimal("300000")
        assert dec(r["personal_deduction"]) == Decimal("300000")
        assert dec(r["taxable_income"]) == Decimal("0")

    def test_child_tax_credit_three_children_and_second_birth(self):
        """3명: 55만 + 40만 = 95만원, 둘째 출산 50만원 → 1,450,000 (제59조의2)."""
        r = call(business_income="80000000", dependents=5, children_count=3, newborn_birth_orders=[2])
        assert dec(r["child_tax_credit"]) == Decimal("1450000")

    @pytest.mark.parametrize(("children", "credit"), [(0, "0"), (1, "250000"), (2, "550000")])
    def test_child_tax_credit_counts(self, children, credit):
        r = call(business_income="80000000", dependents=3, children_count=children)
        assert dec(r["child_tax_credit"]) == Decimal(credit)

    def test_diligent_business_standard_credit(self):
        r = call(business_income="40000000", apply_standard_tax_credit=True, diligent_business_operator=True)
        assert dec(r["standard_tax_credit"]) == Decimal("120000")

    def test_credits_exceeding_tax_floor_at_zero(self):
        r = call(business_income="10000000", other_tax_credits="5000000")
        assert dec(r["decided_tax"]) == Decimal("0")
        assert dec(r["local_income_tax"]) == Decimal("0")

    def test_business_revenue_minus_expenses(self):
        r = call(business_revenue="80000000", business_expenses="30000000")
        assert dec(r["business_income_amount"]) == Decimal("50000000")


class TestErrorsAndPolicy:
    @pytest.mark.parametrize("kwargs", [
        {"total_salary": "-1"},
        {"interest_income": "-1"},
        {"dependents": 0},
        {"elderly_count": 2},
        {"disabled_count": -1},
        {"children_count": 1},
        {"dependents": 2, "children_count": 1, "newborn_birth_orders": [1]},
        {"dependents": 2, "newborn_birth_orders": [0]},
        {"business_income": "1000", "business_revenue": "1000"},
        {"business_revenue": "1000", "business_expenses": "2000"},
        {"other_income_deemed_revenue": "1000", "other_income_actual_expenses": "2000"},
    ])
    def test_invalid_inputs(self, kwargs):
        with pytest.raises(InvalidInputError):
            call(**kwargs)

    def test_before_effective_date(self):
        with pytest.raises(PolicyNotInEffectError):
            call(business_income="10000000", as_of="2025-12-31")

    def test_effective_on_first_day(self):
        r = call(business_income="10000000", as_of="2026-01-01")
        assert r["policy_effective_date"] == "2026-01-01"

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(year=2025, business_income="10000000")

    def test_referenced_policies_listed(self):
        r = call(total_salary="30000000")
        keys = [p["key"] for p in r["referenced_policies"]]
        assert keys == ["tax/kr_income", "tax/kr_withholding", "tax/kr_pension_income"]
        assert r["policy_citations"]
