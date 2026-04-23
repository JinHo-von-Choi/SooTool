"""Tests for tax_us.state_tax tool (CA, NY, TX).

Author: 최진호
Date: 2026-04-23
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
# California: 10-bracket progressive
# ---------------------------------------------------------------------------

class TestCalifornia:
    def test_ca_bracket1_upper_single(self):
        """Single 10756 * 0.01 = 107.56"""
        r = call(taxable_income="10756", state="CA", filing_status="single", year=2025)
        assert r["tax"] == "107.56"
        assert r["marginal_rate"] == "0.01"

    def test_ca_bracket2_upper_single(self):
        """107.56 + 0.02 * (25499-10756) = 107.56 + 294.86 = 402.42"""
        r = call(taxable_income="25499", state="CA", filing_status="single", year=2025)
        assert r["tax"] == "402.42"
        assert r["marginal_rate"] == "0.02"

    def test_ca_mid_bracket(self):
        """100k single: validate falls inside 9.3% bracket (upper 360659)."""
        r = call(taxable_income="100000", state="CA", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.093"
        # 107.56 + 294.86 + 0.04*(40245-25499) + 0.06*(55866-40245)
        # + 0.08*(70606-55866) + 0.093*(100000-70606)
        # = 107.56 + 294.86 + 589.84 + 937.26 + 1179.20 + 2734.64
        # = 5843.36 (allow ±$1 rounding tolerance)
        tax = Decimal(r["tax"])
        assert abs(tax - Decimal("5842.36")) <= Decimal("1")

    def test_ca_top_bracket(self):
        """>1M falls into 13.3% top."""
        r = call(taxable_income="1500000", state="CA", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.133"

    def test_ca_mfj_first_bracket(self):
        """MFJ first bracket = single×2: 21512 × 0.01 = 215.12"""
        r = call(taxable_income="21512", state="CA", filing_status="married_joint", year=2025)
        assert r["tax"] == "215.12"

    def test_ca_standard_deduction(self):
        """Apply std deduction 5540 single: taxable_after drops by 5540."""
        r = call(
            taxable_income="50000",
            state="CA",
            filing_status="single",
            year=2025,
            apply_standard_deduction=True,
        )
        assert r["standard_deduction"] == "5540"
        assert r["taxable_income_after_deduction"] == "44460"


# ---------------------------------------------------------------------------
# New York: 9-bracket progressive
# ---------------------------------------------------------------------------

class TestNewYork:
    def test_ny_bracket1_upper_single(self):
        """Single 8500 × 0.04 = 340.00"""
        r = call(taxable_income="8500", state="NY", filing_status="single", year=2025)
        assert r["tax"] == "340.00"
        assert r["marginal_rate"] == "0.04"

    def test_ny_bracket2_upper_single(self):
        """340 + 0.045 * (11700-8500) = 340 + 144 = 484.00"""
        r = call(taxable_income="11700", state="NY", filing_status="single", year=2025)
        assert r["tax"] == "484.00"
        assert r["marginal_rate"] == "0.045"

    def test_ny_mid_bracket_6pct(self):
        """100k single: up to 80650 bracket; 80650->215400 at 6%."""
        r = call(taxable_income="100000", state="NY", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.06"

    def test_ny_top_bracket(self):
        """> 25M: 10.9% top."""
        r = call(taxable_income="30000000", state="NY", filing_status="single", year=2025)
        assert r["marginal_rate"] == "0.109"

    def test_ny_mfj_first_bracket(self):
        r = call(taxable_income="17150", state="NY", filing_status="married_joint", year=2025)
        # 17150 * 0.04 = 686
        assert r["tax"] == "686.00"

    def test_ny_hoh_first_bracket(self):
        """HoH 12800 × 0.04 = 512."""
        r = call(taxable_income="12800", state="NY", filing_status="head_of_household", year=2025)
        assert r["tax"] == "512.00"

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
