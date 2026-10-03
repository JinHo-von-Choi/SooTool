"""Tests for tax_us.federal_income tool (IRS 2025, 2026 tax years).

기대값은 Rev. Proc. 2024-40 sec. 2.01, Rev. Proc. 2025-32 sec. 3.01, 4.01, 4.14 의
세율표와 표준공제액에서 직접 계산한다.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax_us  # noqa: F401 - registers tools
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    return REGISTRY.invoke("tax_us.federal_income", **kwargs)


# ---------------------------------------------------------------------------
# Single filing status: 7-bracket boundaries
# ---------------------------------------------------------------------------

class TestSingleBrackets:
    def test_zero_income(self):
        r = call(taxable_income="0", filing_status="single", year=2025)
        assert r["tax"] == "0.00"
        assert r["marginal_rate"] == "0"

    def test_bracket1_upper_11925(self):
        """10% × 11925 = 1192.50"""
        r = call(taxable_income="11925", filing_status="single", year=2025)
        assert r["tax"] == "1192.50"
        assert r["marginal_rate"] == "0.1"

    def test_bracket2_upper_48475(self):
        """1192.50 + 12% × (48475-11925) = 1192.50 + 4386 = 5578.50"""
        r = call(taxable_income="48475", filing_status="single", year=2025)
        assert r["tax"] == "5578.50"
        assert r["marginal_rate"] == "0.12"

    def test_bracket3_upper_103350(self):
        """5578.50 + 22% × (103350-48475) = 5578.50 + 12072.50 = 17651.00"""
        r = call(taxable_income="103350", filing_status="single", year=2025)
        assert r["tax"] == "17651.00"
        assert r["marginal_rate"] == "0.22"

    def test_bracket4_upper_197300(self):
        """17651 + 24% × (197300-103350) = 17651 + 22548 = 40199.00"""
        r = call(taxable_income="197300", filing_status="single", year=2025)
        assert r["tax"] == "40199.00"
        assert r["marginal_rate"] == "0.24"

    def test_bracket5_upper_250525(self):
        """40199 + 32% × (250525-197300) = 40199 + 17032 = 57231.00"""
        r = call(taxable_income="250525", filing_status="single", year=2025)
        assert r["tax"] == "57231.00"
        assert r["marginal_rate"] == "0.32"

    def test_bracket6_upper_626350(self):
        """57231 + 35% × (626350-250525) = 57231 + 131538.75 = 188769.75"""
        r = call(taxable_income="626350", filing_status="single", year=2025)
        assert r["tax"] == "188769.75"
        assert r["marginal_rate"] == "0.35"

    def test_bracket7_top_above_626350(self):
        r = call(taxable_income="1000000", filing_status="single", year=2025)
        # 188769.75 + 37% × (1000000-626350) = 188769.75 + 138250.50 = 327020.25
        assert r["tax"] == "327020.25"
        assert r["marginal_rate"] == "0.37"


# ---------------------------------------------------------------------------
# Married filing jointly
# ---------------------------------------------------------------------------

class TestMarriedJointBrackets:
    def test_bracket1_upper_23850(self):
        """10% × 23850 = 2385.00"""
        r = call(taxable_income="23850", filing_status="married_joint", year=2025)
        assert r["tax"] == "2385.00"

    def test_bracket2_upper_96950(self):
        """2385 + 12% × (96950-23850) = 2385 + 8772 = 11157"""
        r = call(taxable_income="96950", filing_status="married_joint", year=2025)
        assert r["tax"] == "11157.00"

    def test_bracket3_upper_206700(self):
        """11157 + 22% × (206700-96950) = 11157 + 24145 = 35302"""
        r = call(taxable_income="206700", filing_status="married_joint", year=2025)
        assert r["tax"] == "35302.00"

    def test_top_bracket_37(self):
        r = call(taxable_income="1000000", filing_status="married_joint", year=2025)
        assert r["marginal_rate"] == "0.37"


# ---------------------------------------------------------------------------
# Married filing separately
# ---------------------------------------------------------------------------

class TestMarriedSeparateBrackets:
    def test_bracket1_upper_11925(self):
        r = call(taxable_income="11925", filing_status="married_separate", year=2025)
        assert r["tax"] == "1192.50"

    def test_bracket6_upper_375800(self):
        # MFS shifts 35->37 boundary at 375800 (vs single 626350)
        r = call(taxable_income="375800", filing_status="married_separate", year=2025)
        # Reuse MFS schedule: up to 250525 same as single -> 57231
        # 57231 + 35% × (375800-250525) = 57231 + 43846.25 = 101077.25
        assert r["tax"] == "101077.25"
        assert r["marginal_rate"] == "0.35"


# ---------------------------------------------------------------------------
# Head of household
# ---------------------------------------------------------------------------

class TestHeadOfHouseholdBrackets:
    def test_bracket1_upper_17000(self):
        """10% × 17000 = 1700"""
        r = call(taxable_income="17000", filing_status="head_of_household", year=2025)
        assert r["tax"] == "1700.00"

    def test_bracket2_upper_64850(self):
        """1700 + 12% × (64850-17000) = 1700 + 5742 = 7442"""
        r = call(taxable_income="64850", filing_status="head_of_household", year=2025)
        assert r["tax"] == "7442.00"


# ---------------------------------------------------------------------------
# Standard deduction
# ---------------------------------------------------------------------------

class TestStandardDeduction:
    def test_no_deduction(self):
        r = call(taxable_income="50000", filing_status="single", year=2025)
        assert r["standard_deduction"] == "0"
        assert r["taxable_income_after_deduction"] == "50000"

    def test_apply_single(self):
        """2025 single 표준공제 15,750 (IRC 63(c)(7), Rev. Proc. 2025-32 sec. 3.01).

        50000-15750=34250; 10%*11925 + 12%*(34250-11925) = 1192.50 + 2679.00 = 3871.50
        """
        r = call(
            taxable_income="50000",
            filing_status="single",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == "15750"
        assert r["taxable_income_after_deduction"] == "34250"
        assert r["tax"] == "3871.50"

    def test_apply_mfj(self):
        """2025 MFJ 표준공제 31,500: 100000-31500=68500."""
        r = call(
            taxable_income="100000",
            filing_status="married_joint",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == "31500"
        assert r["taxable_income_after_deduction"] == "68500"

    @pytest.mark.parametrize(
        ("filing_status", "expected"),
        [("married_separate", "15750"), ("head_of_household", "23625")],
    )
    def test_apply_mfs_hoh_2025(self, filing_status, expected):
        r = call(
            taxable_income="100000",
            filing_status=filing_status,
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == expected

    def test_deduction_floors_at_zero(self):
        """Income less than std deduction -> taxable_after = 0."""
        r = call(
            taxable_income="5000",
            filing_status="single",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["taxable_income_after_deduction"] == "0"
        assert r["tax"] == "0.00"


# ---------------------------------------------------------------------------
# Validation & errors
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tax year 2026 (Rev. Proc. 2025-32 sec. 4.01 Tables 1-4, sec. 4.14(1))
# ---------------------------------------------------------------------------

class TestYear2026:
    def test_single_bracket1_upper(self):
        """10% x 12400 = 1240 (Table 3 인쇄 기준액 1,240)."""
        r = call(taxable_income="12400", filing_status="single", year=2026)
        assert r["tax"] == "1240.00"

    def test_single_bracket2_upper(self):
        """1240 + 12% x (50400-12400) = 1240 + 4560 = 5800 (Table 3)."""
        r = call(taxable_income="50400", filing_status="single", year=2026)
        assert r["tax"] == "5800.00"

    @pytest.mark.parametrize(
        ("filing_status", "income", "expected"),
        [
            # 각 표의 37% 구간 시작 기준액(Rev. Proc. 2025-32 Tables 1-4 인쇄값)
            ("married_joint",     "768700", "206583.50"),
            ("head_of_household", "640600", "191171.00"),
            ("single",            "640600", "192979.25"),
            ("married_separate",  "384350", "103291.75"),
        ],
    )
    def test_top_bracket_base_amounts(self, filing_status, income, expected):
        r = call(taxable_income=income, filing_status=filing_status, year=2026)
        assert r["tax"] == expected
        assert r["marginal_rate"] == "0.35"

    def test_top_rate_above_threshold(self):
        """MFJ 1,000,000: 206583.50 + 37% x (1000000-768700) = 206583.50 + 85581 = 292164.50."""
        r = call(taxable_income="1000000", filing_status="married_joint", year=2026)
        assert r["tax"] == "292164.50"
        assert r["marginal_rate"] == "0.37"

    @pytest.mark.parametrize(
        ("filing_status", "expected"),
        [
            ("single",            "16100"),
            ("married_joint",     "32200"),
            ("married_separate",  "16100"),
            ("head_of_household", "24150"),
        ],
    )
    def test_standard_deduction_2026(self, filing_status, expected):
        r = call(
            taxable_income="100000",
            filing_status=filing_status,
            year=2026,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == expected

    def test_policy_citations_present(self):
        r = call(taxable_income="50000", filing_status="single", year=2026)
        assert r["policy_version"]["year"] == 2026
        assert r["policy_citations"]


class TestSurvivingSpouse:
    def test_uses_joint_schedule_and_deduction(self):
        """생존 배우자는 공동 신고 표(IRC 1(j)(2)(A))와 같은 표준공제 31,500."""
        qss = call(
            taxable_income="200000",
            filing_status="qualifying_surviving_spouse",
            year=2025,
            apply_standard_deduction=True,
        )
        mfj = call(
            taxable_income="200000",
            filing_status="married_joint",
            year=2025,
            apply_standard_deduction=True,
        )
        assert qss["standard_deduction"] == "31500"
        assert qss["tax"] == mfj["tax"]
        assert qss["filing_status"] == "qualifying_surviving_spouse"


class TestValidation:
    def test_invalid_filing_status(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="50000", filing_status="invalid", year=2025)

    def test_negative_income(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="-100", filing_status="single", year=2025)

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(taxable_income="50000", filing_status="single", year=2099)

    def test_policy_version_fields(self):
        r = call(taxable_income="50000", filing_status="single", year=2025)
        pv = r["policy_version"]
        assert pv["year"] == 2025
        assert "sha256" in pv
        assert "effective_date" in pv
        assert "notice_no" in pv


class TestPolicyLoader:
    def test_load_via_policies_module(self):
        """Verify policy loader path: sootool.policies.load('tax_us', ...)."""
        from sootool.policies import load as pkg_load
        doc = pkg_load("tax_us", "federal_income", 2025)
        assert "data" in doc
        assert "policy_version" in doc
        assert doc["policy_version"]["year"] == 2025

    def test_effective_rate_between_zero_and_one(self):
        r = call(taxable_income="100000", filing_status="single", year=2025)
        eff = Decimal(r["effective_rate"])
        assert eff > Decimal("0")
        assert eff < Decimal("1")
