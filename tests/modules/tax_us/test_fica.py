"""tax_us.fica 시험.

기대값은 IRC 3101, 3111, 3102(f), 1401, 1402 조문, SSA 고시(89 FR 85276, 90 FR 49047)의 사회보장
기준액, IRS Publication 15 (2025, 2026) sec. 9, Schedule SE (2025) 줄 단위 계산, Form 8959 안내와
IRS "Questions and Answers for the Additional Medicare Tax" 예시에서 손으로 구한다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax_us  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    return REGISTRY.invoke("tax_us.fica", **kwargs)


# ---------------------------------------------------------------------------
# 근로자·고용주 FICA (IRC 3101(a)·(b)(1), 3111(a)·(b), 3121(a)(1))
# ---------------------------------------------------------------------------

class TestEmployeeBasic:
    def test_ordinary_wages_2026(self):
        """100,000: OASDI 6,200.00, HI 1,450.00 (근로자·고용주 각각), 추가 Medicare 없음."""
        r = call(year=2026, wages="100000")
        assert r["employee"] == {
            "social_security_tax":     "6200.00",
            "medicare_tax":            "1450.00",
            "additional_medicare_tax": "0.00",
            "total":                   "7650.00",
        }
        assert r["employer"]["total"] == "7650.00"
        assert r["employer"]["additional_medicare_tax"] == "0.00"
        assert "additional_medicare_liability" not in r

    def test_wage_base_2025_is_176100(self):
        """Pub. 15 (2025): 기준액 176,100, 최대 OASDI 176,100 x 6.2% = 10,918.20."""
        r = call(year=2025, wages="176100")
        assert r["social_security_wage_base"] == "176100"
        assert r["employee"]["social_security_tax"] == "10918.20"

    def test_wage_base_2026_is_184500(self):
        """90 FR 49047, Pub. 15 (2026): 기준액 184,500, 최대 OASDI 184,500 x 6.2% = 11,439.00."""
        r = call(year=2026, wages="184500")
        assert r["social_security_wage_base"] == "184500"
        assert r["employee"]["social_security_tax"] == "11439.00"
        assert r["employer"]["social_security_tax"] == "11439.00"

    def test_one_cent_over_wage_base(self):
        """184,500.01: OASDI 는 기준액에서 멈추고 HI 는 전액. 184,500.01 x 1.45% = 2,675.250145 -> 2,675.25."""
        r = call(year=2026, wages="184500.01")
        assert r["social_security_taxable_wages"] == "184500"
        assert r["employee"]["social_security_tax"] == "11439.00"
        assert r["employee"]["medicare_tax"] == "2675.25"

    def test_zero_wages(self):
        r = call(year=2026, wages="0")
        assert r["employee"]["total"] == "0.00"
        assert r["employer"]["total"] == "0.00"


class TestAdditionalMedicareWithholding:
    def test_exactly_200000_no_withholding(self):
        """IRC 3102(f)(1): 200,000 초과분만 원천징수."""
        r = call(year=2026, wages="200000")
        assert r["employee"]["additional_medicare_tax"] == "0.00"
        assert r["additional_medicare_withholding_base"] == "0"

    def test_bonus_example_230000(self):
        """IRS Q&A 예시 M: 180,000 + 보너스 50,000 -> 30,000 에 원천징수, 30,000 x 0.9% = 270.00."""
        r = call(year=2025, wages="230000")
        assert r["additional_medicare_withholding_base"] == "30000"
        assert r["employee"]["additional_medicare_tax"] == "270.00"
        # 근로자: 10,918.20 + 230,000 x 1.45% (3,335.00) + 270.00
        assert r["employee"]["total"] == "14523.20"
        # 고용주: 추가 Medicare 부담분 없음, 10,918.20 + 3,335.00
        assert r["employer"]["total"] == "14253.20"

    def test_withholding_ignores_filing_status(self):
        """IRS Q&A: 각 150,000 인 부부 직원은 공동 임계값 250,000 을 넘어도 원천징수하지 않는다.
        신고 정산액은 (150,000 + 150,000 - 250,000) x 0.9% = 450.00."""
        r = call(year=2026, wages="150000", filing_status="married_joint", other_medicare_wages="150000")
        assert r["employee"]["additional_medicare_tax"] == "0.00"
        assert r["additional_medicare_filing_threshold"] == "250000"
        assert r["additional_medicare_liability_base"] == "50000"
        assert r["additional_medicare_liability"] == "450.00"


class TestAdditionalMedicareFiling:
    def test_married_separate_example_f(self):
        """IRS Q&A 예시 3(F): 부부 개별, 임금 175,000 -> (175,000 - 125,000) x 0.9% = 450.00, 원천징수 0."""
        r = call(year=2025, wages="175000", filing_status="married_separate")
        assert r["additional_medicare_liability_base"] == "50000"
        assert r["additional_medicare_liability"] == "450.00"
        assert r["employee"]["additional_medicare_tax"] == "0.00"

    def test_head_of_household_example_g(self):
        """IRS Q&A 예시 4(G): 세대주, 임금 225,000 -> 원천징수와 신고 정산 모두 25,000 x 0.9% = 225.00."""
        r = call(year=2025, wages="225000", filing_status="head_of_household")
        assert r["employee"]["additional_medicare_tax"] == "225.00"
        assert r["additional_medicare_liability"] == "225.00"

    def test_qualifying_surviving_spouse_uses_200000(self):
        """Form 8959 안내 임계값 표: 생존 배우자는 200,000 (공동 신고 250,000 이 아님)."""
        r = call(year=2026, wages="210000", filing_status="qualifying_surviving_spouse")
        assert r["additional_medicare_filing_threshold"] == "200000"
        assert r["additional_medicare_liability"] == "90.00"

    def test_single_threshold_boundary(self):
        r = call(year=2026, wages="200000", filing_status="single")
        assert r["additional_medicare_liability"] == "0.00"


# ---------------------------------------------------------------------------
# 자영업세 SECA (IRC 1401, 1402, Schedule SE Part I)
# ---------------------------------------------------------------------------

class TestSelfEmployed:
    def test_schedule_se_basic_2026(self):
        """순이익 100,000: 92,350 x 12.4% = 11,451.40, 92,350 x 2.9% = 2,678.15,
        자영업세 14,129.55, 공제 50% = 7,064.775 -> HALF_UP 7,064.78."""
        r = call(year=2026, mode="self_employed", net_profit="100000", filing_status="single")
        assert Decimal(r["net_earnings"]) == Decimal("92350")
        assert r["social_security_tax"] == "11451.40"
        assert r["medicare_tax"] == "2678.15"
        assert r["self_employment_tax"] == "14129.55"
        assert r["self_employment_tax_deduction"] == "7064.78"
        assert r["additional_medicare_tax"] == "0.00"
        assert r["self_employment_total"] == "14129.55"
        assert "employee" not in r

    def test_wages_reduce_social_security_room_2025(self):
        """Schedule SE (2025) line 7-10: (176,100 - 150,000) = 26,100 x 12.4% = 3,236.40, HI 는 전액 2,678.15."""
        r = call(year=2025, mode="self_employed", net_profit="100000", wages="150000", filing_status="single")
        assert Decimal(r["social_security_taxable_earnings"]) == Decimal("26100")
        assert r["social_security_tax"] == "3236.40"
        assert r["medicare_tax"] == "2678.15"
        assert r["self_employment_tax"] == "5914.55"

    def test_wages_over_base_leave_only_medicare(self):
        """임금이 기준액 이상이면 line 9 가 0 이고 OASDI 0."""
        r = call(year=2026, mode="self_employed", net_profit="10000", wages="190000", filing_status="single")
        assert r["social_security_tax"] == "0.00"
        # 9,235 x 2.9% = 267.815 -> 267.82
        assert r["medicare_tax"] == "267.82"

    def test_minimum_400_boundary(self):
        """IRC 1402(b)(2): 433 x 0.9235 = 399.8755 < 400 -> 0, 434 x 0.9235 = 400.799 -> 과세."""
        below = call(year=2026, mode="self_employed", net_profit="433", filing_status="single")
        assert below["below_minimum"] is True
        assert below["self_employment_total"] == "0.00"
        above = call(year=2026, mode="self_employed", net_profit="434", filing_status="single")
        assert above["below_minimum"] is False
        # 400.799 x 12.4% = 49.699076 -> 49.70, 400.799 x 2.9% = 11.623171 -> 11.62
        assert above["social_security_tax"] == "49.70"
        assert above["medicare_tax"] == "11.62"

    def test_loss_is_not_taxed(self):
        r = call(year=2026, mode="self_employed", net_profit="-5000", filing_status="single")
        assert r["below_minimum"] is True
        assert r["self_employment_total"] == "0.00"


class TestSelfEmployedAdditionalMedicare:
    def test_single_threshold_reduced_by_wages_example_c(self):
        """IRS Q&A 예시 1(C): 단독, 임금 130,000 -> 자영업 임계값 200,000 - 130,000 = 70,000.
        순이익 200,000 -> 순자영업소득 184,700, 추가 Medicare (184,700 - 70,000) x 0.9% = 1,032.30."""
        r = call(year=2026, mode="self_employed", net_profit="200000", wages="130000", filing_status="single")
        assert r["additional_medicare_filing_threshold"] == "70000"
        assert Decimal(r["additional_medicare_liability_base"]) == Decimal("114700")
        assert r["additional_medicare_tax"] == "1032.30"

    def test_joint_spouse_wages_reduce_threshold_form_8959(self):
        """Form 8959 안내 예시: 공동 신고, 배우자 임금 130,000 -> 임계값 250,000 - 130,000 = 120,000."""
        r = call(
            year=2025, mode="self_employed", net_profit="160000",
            other_medicare_wages="130000", filing_status="married_joint",
        )
        assert r["additional_medicare_filing_threshold"] == "120000"
        # 160,000 x 0.9235 = 147,760, (147,760 - 120,000) x 0.9% = 249.84
        assert r["additional_medicare_tax"] == "249.84"
        # 배우자 임금은 본인의 OASDI 한도를 줄이지 않는다: 147,760 x 12.4% = 18,322.24
        assert r["social_security_tax"] == "18322.24"

    def test_threshold_not_below_zero_example_f(self):
        """IRS Q&A 예시 3(F): 부부 개별, 임금 175,000 -> 임계값 125,000 은 0 으로 줄고 0 미만이 되지 않는다."""
        r = call(year=2025, mode="self_employed", net_profit="50000", wages="175000", filing_status="married_separate")
        assert r["additional_medicare_filing_threshold"] == "0"
        # 50,000 x 0.9235 = 46,175, 46,175 x 0.9% = 415.575 -> 415.58
        assert r["additional_medicare_tax"] == "415.58"
        # 175,000 < 176,100 이므로 OASDI 한도 1,100: 1,100 x 12.4% = 136.40
        assert r["social_security_tax"] == "136.40"

    def test_deduction_excludes_additional_medicare(self):
        """IRC 164(f)·Schedule SE line 13: 공제는 자영업세(12.4%+2.9%)의 50% 이며 추가 Medicare 제외."""
        r = call(year=2026, mode="self_employed", net_profit="400000", filing_status="single")
        # NE 369,400: OASDI 184,500 x 12.4% = 22,878.00, HI 369,400 x 2.9% = 10,712.60
        assert r["self_employment_tax"] == "33590.60"
        assert r["self_employment_tax_deduction"] == "16795.30"
        # (369,400 - 200,000) x 0.9% = 1,524.60
        assert r["additional_medicare_tax"] == "1524.60"
        assert r["self_employment_total"] == "35115.20"


# ---------------------------------------------------------------------------
# 정책 시점과 입력 오류
# ---------------------------------------------------------------------------

class TestPolicyPeriods:
    def test_as_of_inside_2026(self):
        r = call(year=2026, wages="190000", as_of="2026-10-03")
        assert r["policy_effective_date"] == "2026-01-01"
        assert r["employee"]["social_security_tax"] == "11439.00"

    def test_as_of_before_2026_effective_date(self):
        with pytest.raises(PolicyNotInEffectError):
            call(year=2026, wages="190000", as_of="2025-12-31")

    def test_as_of_after_2025_effective_to(self):
        with pytest.raises(PolicyNotInEffectError):
            call(year=2025, wages="190000", as_of="2026-01-01")

    def test_same_wages_differ_by_year(self):
        """190,000: 2025 은 176,100 에서, 2026 은 184,500 에서 OASDI 가 멈춘다."""
        assert call(year=2025, wages="190000")["employee"]["social_security_tax"] == "10918.20"
        assert call(year=2026, wages="190000")["employee"]["social_security_tax"] == "11439.00"

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(year=2024, wages="1000")

    def test_citations_present(self):
        r = call(year=2026, wages="1000")
        articles = " ".join(c.get("article", "") for c in r["policy_citations"])
        assert "3101(b)(2)" in articles
        assert "1402(a)(12)" in articles


class TestInvalidInput:
    def test_unknown_mode(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, mode="household", wages="1000")

    def test_negative_wages(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, wages="-1")

    def test_net_profit_in_employee_mode(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, wages="1000", net_profit="500")

    def test_self_employed_requires_filing_status(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, mode="self_employed", net_profit="50000")

    def test_other_wages_without_filing_status(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, wages="1000", other_medicare_wages="1000")

    def test_unknown_filing_status(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, wages="1000", filing_status="joint")

    def test_infinite_amount(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, wages="Infinity")

    def test_bad_rounding(self):
        with pytest.raises(InvalidInputError):
            call(year=2026, wages="1000", rounding="BANKERS")
