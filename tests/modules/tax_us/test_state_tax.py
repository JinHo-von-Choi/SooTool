"""Tests for tax_us.state_tax tool (CA, NY, TX).

기대값은 FTB 2025 세율 스케줄과 Form 540 안내서, NY IT-201-I (2025) 세율표와 세액 계산
워크시트, NY IT-2105-I (2026) 에서 직접 계산한다.

Author: 최진호
Date: 2026-04-23
Modified: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax_us  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    return REGISTRY.invoke("tax_us.state_tax", **kwargs)


# ---------------------------------------------------------------------------
# Texas: no income tax (short-circuit)
# ---------------------------------------------------------------------------

class TestTexas:
    def test_tx_zero_tax_any_income(self):
        r = call(taxable_income="100000", state="TX", filing_status="single", year=2025)
        assert r["tax"] == "0"
        assert r["has_income_tax"] is False
        assert r["marginal_rate"] == "0"
        assert r["breakdown"] == []

    def test_tx_large_income_still_zero(self):
        r = call(taxable_income="5000000", state="TX", filing_status="married_joint", year=2025)
        assert r["tax"] == "0"
        assert r["has_income_tax"] is False

    def test_tx_standard_deduction_ignored(self):
        r = call(
            taxable_income="100000",
            state="TX",
            filing_status="single",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["tax"] == "0"


# ---------------------------------------------------------------------------
# California 2025: FTB Schedules X, Y, Z + Behavioral Health Services Tax
# 기대값 = 표 인쇄 기준액 + 세율 x (과세표준 - 구간 하한), 1,000,000 초과분 1% 가산
# ---------------------------------------------------------------------------

class TestCalifornia:
    def test_ca_bracket1_upper_single(self):
        """Schedule X: 11079 x 1% = 110.79 (다음 구간 인쇄 기준액)."""
        r = call(taxable_income="11079", state="CA", filing_status="single", year=2025)
        assert r["tax"] == "110.79"
        assert r["marginal_rate"] == "0.01"

    def test_ca_bracket2_upper_single(self):
        """110.79 + 2% x (26264-11079) = 110.79 + 303.70 = 414.49 (인쇄 기준액)."""
        r = call(taxable_income="26264", state="CA", filing_status="single", year=2025)
        assert r["tax"] == "414.49"
        assert r["marginal_rate"] == "0.02"

    def test_ca_mid_bracket(self):
        """100000 single: 3201.97 + 9.3% x (100000-72724) = 3201.97 + 2536.67 = 5738.64."""
        r = call(taxable_income="100000", state="CA", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.093"
        assert r["tax"] == "5738.64"

    def test_ca_ftb_example_mfj(self):
        """FTB 2025 세율 스케줄 예시: MFJ 125000 -> 3974.82 + 8% x 9916 = 4768.10."""
        r = call(taxable_income="125000", state="CA", filing_status="married_joint", year=2025)
        assert r["tax"] == "4768.10"

    def test_ca_mfj_first_bracket(self):
        """Schedule Y 첫 구간: 22158 x 1% = 221.58."""
        r = call(taxable_income="22158", state="CA", filing_status="married_joint", year=2025)
        assert r["tax"] == "221.58"

    def test_ca_hoh_first_bracket(self):
        """Schedule Z 첫 구간: 22173 x 1% = 221.73."""
        r = call(taxable_income="22173", state="CA", filing_status="head_of_household", year=2025)
        assert r["tax"] == "221.73"

    def test_ca_standard_deduction(self):
        """2025 표준공제 single 5706: 50000-5706 = 44294."""
        r = call(
            taxable_income="50000",
            state="CA",
            filing_status="single",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == "5706"
        assert r["taxable_income_after_deduction"] == "44294"

    @pytest.mark.parametrize(
        ("filing_status", "expected"),
        [("married_joint", "11412"), ("head_of_household", "11412"), ("married_separate", "5706")],
    )
    def test_ca_standard_deduction_other_statuses(self, filing_status, expected):
        r = call(
            taxable_income="50000",
            state="CA",
            filing_status=filing_status,
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == expected

    def test_ca_top_bracket_single(self):
        """1500000 single: 72219.84 + 12.3% x 757047 (93116.78) + 1% x 500000 = 170336.62."""
        r = call(taxable_income="1500000", state="CA", filing_status="single", year=2025)
        assert r["tax"] == "170336.62"
        assert r["marginal_rate"] == "0.133"
        assert r["surcharge"]["amount"] == "5000.00"

    def test_ca_mfj_surcharge_starts_at_one_million(self):
        """MFJ 1200000: 77276.52 + 11.3% x 308458 (34855.75) + 1% x 200000 = 114132.27.

        가산세 임계액은 신고 유형과 무관하게 1,000,000 이다.
        """
        r = call(taxable_income="1200000", state="CA", filing_status="married_joint", year=2025)
        assert r["tax"] == "114132.27"
        assert r["marginal_rate"] == "0.123"
        assert r["surcharge"]["base"] == "200000"

    def test_ca_hoh_between_million_and_top_bracket(self):
        """HoH 1005000: 51802.15 + 11.3% x 398749 (45058.64) + 1% x 5000 = 96910.79."""
        r = call(
            taxable_income="1005000", state="CA", filing_status="head_of_household", year=2025,
        )
        assert r["tax"] == "96910.79"
        assert r["marginal_rate"] == "0.123"

    def test_ca_no_surcharge_at_one_million(self):
        """정확히 1,000,000 은 초과분이 없다.

        single: 72219.84 + 12.3% x 257047 (31616.781) = 103836.621 -> 103836.62
        """
        r = call(taxable_income="1000000", state="CA", filing_status="single", year=2025)
        assert r["tax"] == "103836.62"
        assert Decimal(r["surcharge"]["amount"]) == Decimal("0")
        assert r["marginal_rate"] == "0.123"

    def test_ca_2026_not_published(self):
        """FTB 2026 세율 스케줄 미공표: 2026 정책 없음."""
        with pytest.raises(UnsupportedPolicyError):
            call(taxable_income="50000", state="CA", filing_status="single", year=2026)


# ---------------------------------------------------------------------------
# New York 2025: IT-201-I rate schedule (인쇄 기준액) and tax computation worksheets
# ---------------------------------------------------------------------------

class TestNewYork:
    def test_ny_bracket1_upper_single(self):
        """Single 8500 x 0.04 = 340.00"""
        r = call(taxable_income="8500", state="NY", filing_status="single", year=2025)
        assert r["tax"] == "340.00"
        assert r["marginal_rate"] == "0.04"

    def test_ny_bracket2_upper_single(self):
        """340 + 0.045 * (11700-8500) = 340 + 144 = 484.00"""
        r = call(taxable_income="11700", state="NY", filing_status="single", year=2025)
        assert r["tax"] == "484.00"
        assert r["marginal_rate"] == "0.045"

    def test_ny_printed_base_amount(self):
        """Single 20000: 표 '600 plus 5.5% of the excess over 13,900' -> 600 + 335.50 = 935.50."""
        r = call(taxable_income="20000", state="NY", filing_status="single", year=2025)
        assert r["tax"] == "935.50"

    def test_ny_mid_bracket_6pct(self):
        """100k single, NYAGI 100k (107,650 이하): 4271 + 6% x 19350 = 5432.00."""
        r = call(taxable_income="100000", state="NY", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.06"
        assert r["tax"] == "5432.00"
        assert r["recapture"]["method"] == "schedule"

    def test_ny_top_bracket(self):
        """NYAGI 30M > 25M: worksheet 11, 과세표준 전액 10.9% = 3270000.00."""
        r = call(taxable_income="30000000", state="NY", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.109"
        assert r["tax"] == "3270000.00"

    def test_ny_mfj_first_bracket(self):
        r = call(taxable_income="17150", state="NY", filing_status="married_joint", year=2025)
        # 17150 * 0.04 = 686
        assert r["tax"] == "686.00"

    def test_ny_hoh_first_bracket(self):
        """HoH 12800 × 0.04 = 512."""
        r = call(taxable_income="12800", state="NY", filing_status="head_of_household", year=2025)
        assert r["tax"] == "512.00"

    def test_ny_mfs_uses_single_schedule(self):
        """MFS 는 Single 과 같은 스케줄(6% 구간 상한 215,400).

        과세표준 200000, NYAGI 200000 >= 157,650: worksheet 7 line 3 = 200000 x 6% = 12000.00
        """
        mfs    = call(taxable_income="200000", state="NY", filing_status="married_separate", year=2025)
        single = call(taxable_income="200000", state="NY", filing_status="single", year=2025)
        assert mfs["tax"] == "12000.00"
        assert mfs["marginal_rate"] == "0.06"
        assert mfs["tax"] == single["tax"]

    def test_ny_standard_deduction(self):
        r = call(
            taxable_income="50000",
            state="NY",
            filing_status="single",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == "8000"
        assert r["taxable_income_after_deduction"] == "42000"


class TestNewYorkRecapture:
    def test_worksheet1_phase_in(self):
        """MFJ worksheet 1: 과세표준 120000, NYAGI 132650.

        line 3 = 120000 x 5.5% = 6600; line 4 = 1202 + 5.5% x 92100 = 6267.50
        line 5 = 332.50; line 7 = 25000 / 50000 = 0.5; line 8 = 166.25
        line 9 = 6267.50 + 166.25 = 6433.75
        """
        r = call(
            taxable_income="120000", state="NY", filing_status="married_joint", year=2025,
            state_agi="132650",
        )
        assert r["tax"] == "6433.75"
        assert r["recapture"]["method"] == "first_phase_in"
        assert r["recapture"]["ratio"] == "0.5000"

    def test_worksheet1_full_flat(self):
        """MFJ worksheet 1: NYAGI 160000 >= 157650 이면 line 3 = 150000 x 5.5% = 8250.00."""
        r = call(
            taxable_income="150000", state="NY", filing_status="married_joint", year=2025,
            state_agi="160000",
        )
        assert r["tax"] == "8250.00"

    def test_worksheet8_single_step(self):
        """Single worksheet 8: 과세표준 300000, NYAGI 300000.

        line 3 = 12356 + 6.85% x 84600 = 18151.10; line 4 = 568; line 5 = 1831
        line 8 = min(84600, 50000) / 50000 = 1; line 10 = 18151.10 + 568 + 1831 = 20550.10
        """
        r = call(taxable_income="300000", state="NY", filing_status="single", year=2025)
        assert r["tax"] == "20550.10"
        assert r["recapture"]["method"] == "step"

    def test_worksheet3_partial_ratio(self):
        """MFJ worksheet 3: 과세표준 330000, NYAGI 343200.

        line 3 = 18252 + 6.85% x 6800 = 18717.80; line 4 = 1140; line 5 = 2747
        line 8 = 20000 / 50000 = 0.4; line 9 = 1098.80; line 10 = 20956.60
        """
        r = call(
            taxable_income="330000", state="NY", filing_status="married_joint", year=2025,
            state_agi="343200",
        )
        assert r["tax"] == "20956.60"

    def test_worksheet6_flat_over_25m_agi(self):
        """MFJ worksheet 6: NYAGI 26M > 25M 이면 과세표준 24M x 10.9% = 2616000.00."""
        r = call(
            taxable_income="24000000", state="NY", filing_status="married_joint", year=2025,
            state_agi="26000000",
        )
        assert r["tax"] == "2616000.00"
        assert r["marginal_rate"] == "0.109"

    def test_worksheet13_hoh_step(self):
        """HoH worksheet 13: 과세표준 280000, NYAGI 290000.

        line 3 = 15371 + 6.85% x 10700 = 16103.95; line 4 = 787; line 5 = 2289
        line 8 = 20700 / 50000 = 0.414; line 9 = 947.646; line 10 = 17838.596 -> 17838.60
        """
        r = call(
            taxable_income="280000", state="NY", filing_status="head_of_household", year=2025,
            state_agi="290000",
        )
        assert r["tax"] == "17838.60"

    def test_agi_at_threshold_uses_schedule(self):
        """NYAGI 107650 이하는 스케줄 세액: MFJ 100000 -> 1202 + 5.5% x 72100 = 5167.50."""
        r = call(
            taxable_income="100000", state="NY", filing_status="married_joint", year=2025,
            state_agi="107650",
        )
        assert r["tax"] == "5167.50"

    def test_negative_state_agi_rejected(self):
        with pytest.raises(InvalidInputError):
            call(
                taxable_income="100000", state="NY", filing_status="single", year=2025,
                state_agi="-1",
            )


# ---------------------------------------------------------------------------
# New York 2026: IT-2105-I (2026) rates and worksheets
# ---------------------------------------------------------------------------

class TestNewYork2026:
    def test_first_bracket_rate(self):
        """8500 x 3.90% = 331.50 (표 인쇄 기준액 332 는 다음 구간부터 사용)."""
        r = call(taxable_income="8500", state="NY", filing_status="single", year=2026)
        assert r["tax"] == "331.50"
        assert r["marginal_rate"] == "0.039"

    def test_printed_base_second_bracket(self):
        """Single 10000: '332 plus 4.40% of the excess over 8,500' -> 332 + 66 = 398.00."""
        r = call(taxable_income="10000", state="NY", filing_status="single", year=2026)
        assert r["tax"] == "398.00"

    def test_mfj_mid_bracket(self):
        """MFJ 100000, NYAGI 100000: 1174 + 5.40% x 72100 = 1174 + 3893.40 = 5067.40."""
        r = call(taxable_income="100000", state="NY", filing_status="married_joint", year=2026)
        assert r["tax"] == "5067.40"
        assert r["marginal_rate"] == "0.054"

    def test_worksheet7_flat(self):
        """Single worksheet 7: NYAGI 200000 >= 157650, line 3 = 200000 x 5.90% = 11800.00."""
        r = call(taxable_income="200000", state="NY", filing_status="single", year=2026)
        assert r["tax"] == "11800.00"

    def test_worksheet3_mfj(self):
        """MFJ worksheet 3 (2026): 과세표준 400000, NYAGI 400000.

        line 3 = 17928 + 6.85% x 76800 = 23188.80; line 4 = 1140; line 5 = 3071; line 8 = 1
        line 10 = 23188.80 + 1140 + 3071 = 27399.80
        """
        r = call(taxable_income="400000", state="NY", filing_status="married_joint", year=2026)
        assert r["tax"] == "27399.80"

    def test_standard_deduction(self):
        r = call(
            taxable_income="50000", state="NY", filing_status="head_of_household", year=2026,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == "11200"


class TestTexas2026:
    def test_tx_2026_no_income_tax(self):
        r = call(taxable_income="100000", state="TX", filing_status="single", year=2026)
        assert r["tax"] == "0"
        assert r["has_income_tax"] is False


class TestSurvivingSpouseState:
    def test_ny_uses_joint_schedule(self):
        qss = call(
            taxable_income="100000", state="NY", filing_status="qualifying_surviving_spouse",
            year=2025, apply_standard_deduction=True,
        )
        assert qss["standard_deduction"] == "16050"
        mfj = call(
            taxable_income="100000", state="NY", filing_status="married_joint",
            year=2025, apply_standard_deduction=True,
        )
        assert qss["tax"] == mfj["tax"]


# ---------------------------------------------------------------------------
# Validation & errors
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_state(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="50000", state="FL", filing_status="single", year=2025)

    def test_invalid_filing_status(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="50000", state="CA", filing_status="xx", year=2025)

    def test_negative_income(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="-1", state="CA", filing_status="single", year=2025)

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(taxable_income="50000", state="CA", filing_status="single", year=2099)

    def test_trace_tool_name(self):
        r = call(taxable_income="50000", state="CA", filing_status="single", year=2025)
        assert r["trace"]["tool"] == "tax_us.state_tax"

    def test_policy_version_fields_all_states(self):
        for state in ("CA", "NY", "TX"):
            r = call(taxable_income="50000", state=state, filing_status="single", year=2025)
            pv = r["policy_version"]
            assert pv["year"] == 2025
            assert len(pv["sha256"]) == 64


class TestPolicyLoader:
    def test_load_ca_policy(self):
        from sootool.policies import load as pkg_load
        doc = pkg_load("tax_us", "state_tax_ca", 2025)
        assert doc["data"]["has_income_tax"] is True

    def test_load_tx_policy_no_income_tax(self):
        from sootool.policies import load as pkg_load
        doc = pkg_load("tax_us", "state_tax_tx", 2025)
        assert doc["data"]["has_income_tax"] is False

    def test_load_ny_policy(self):
        from sootool.policies import load as pkg_load
        doc = pkg_load("tax_us", "state_tax_ny", 2025)
        assert "brackets" in doc["data"]
        assert "single" in doc["data"]["brackets"]
