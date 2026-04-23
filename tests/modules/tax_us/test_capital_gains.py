"""Tests for tax_us.capital_gains tool (LTCG + NIIT).

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax_us  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax_us.capital_gains", **kwargs)


# ---------------------------------------------------------------------------
# Long-term capital gains: 0%/15%/20% boundaries per filing status
# ---------------------------------------------------------------------------

class TestLTCGSingle:
    def test_zero_bracket(self):
        """Under 48350: 0% rate -> tax=0."""
        r = call(gain="48350", filing_status="single", year=2025, term="long")
        assert r["tax"] == "0.00"
        # Decimal drops trailing zeros; 0.00 -> "0.0"
        assert Decimal(r["marginal_rate"]) == Decimal("0")

    def test_15_percent_bracket(self):
        """100k: (100000-48350)*0.15 = 7747.50"""
        r = call(gain="100000", filing_status="single", year=2025, term="long")
        assert r["tax"] == "7747.50"
        assert r["marginal_rate"] == "0.15"

    def test_15_pct_upper_boundary(self):
        """533400: (533400-48350)*0.15 = 72757.50"""
        r = call(gain="533400", filing_status="single", year=2025, term="long")
        assert r["tax"] == "72757.50"
        assert r["marginal_rate"] == "0.15"

    def test_20_percent_bracket(self):
        """600k: 72757.50 + (600000-533400)*0.20 = 72757.50 + 13320 = 86077.50"""
        r = call(gain="600000", filing_status="single", year=2025, term="long")
        assert r["tax"] == "86077.50"
        assert Decimal(r["marginal_rate"]) == Decimal("0.20")


class TestLTCGMarriedJoint:
    def test_zero_bracket(self):
        r = call(gain="96700", filing_status="married_joint", year=2025, term="long")
        assert r["tax"] == "0.00"

    def test_15_pct(self):
        """200k: (200000-96700)*0.15 = 15495"""
        r = call(gain="200000", filing_status="married_joint", year=2025, term="long")
        assert r["tax"] == "15495.00"


class TestLTCGMarriedSeparate:
    def test_zero_bracket(self):
        r = call(gain="48350", filing_status="married_separate", year=2025, term="long")
        assert r["tax"] == "0.00"

    def test_15_pct_upper_boundary_300k(self):
        """MFS 15% upper = 300000: (300000-48350)*0.15 = 37747.50"""
        r = call(gain="300000", filing_status="married_separate", year=2025, term="long")
        assert r["tax"] == "37747.50"


class TestLTCGHeadOfHousehold:
    def test_zero_bracket_upper_64750(self):
        r = call(gain="64750", filing_status="head_of_household", year=2025, term="long")
        assert r["tax"] == "0.00"

    def test_15_pct(self):
        """100k: (100000-64750)*0.15 = 5287.50"""
        r = call(gain="100000", filing_status="head_of_household", year=2025, term="long")
        assert r["tax"] == "5287.50"


# ---------------------------------------------------------------------------
# Short-term: delegates to federal_income
# ---------------------------------------------------------------------------

class TestShortTerm:
    def test_short_single_50k(self):
        """Same as federal_income 50k single = 5914.00."""
        r = call(gain="50000", filing_status="single", year=2025, term="short")
        assert r["tax"] == "5914.00"
        assert r["term"] == "short"

    def test_short_with_ordinary_income(self):
        """ordinary_taxable_income overrides gain for rate calc."""
        r = call(
            gain="10000",
            filing_status="single",
            year=2025,
            term="short",
            ordinary_taxable_income="50000",
        )
        assert r["tax"] == "5914.00"


# ---------------------------------------------------------------------------
# Net Investment Income Tax (NIIT) 3.8%
# ---------------------------------------------------------------------------

class TestNIIT:
    def test_niit_off_default(self):
        r = call(gain="300000", filing_status="single", year=2025, term="long")
        assert r["niit"] == "0"

    def test_niit_below_threshold(self):
        """Single threshold 200k. MAGI 180k -> no NIIT."""
        r = call(
            gain="50000",
            filing_status="single",
            year=2025,
            term="long",
            magi="180000",
            apply_niit=True,
        )
        assert r["niit"] == "0.00"

    def test_niit_above_threshold_single(self):
        """Single threshold 200k. MAGI 300k, gain 50k.
        excess = 300k - 200k = 100k; niit_base = min(50k, 100k) = 50k
        niit = 50000 × 0.038 = 1900.00
        LTCG tax = (50000-48350)*0.15 = 247.50
        total = 247.50 + 1900 = 2147.50
        """
        r = call(
            gain="50000",
            filing_status="single",
            year=2025,
            term="long",
            magi="300000",
            apply_niit=True,
        )
        assert r["niit"] == "1900.00"
        assert r["ltcg_tax"] == "247.50"
        assert r["tax"] == "2147.50"

    def test_niit_mfj_threshold(self):
        """MFJ threshold 250k. MAGI 260k, gain 100k.
        excess = 10k; niit_base = min(100k, 10k) = 10k; niit = 380.00
        LTCG = (100000-96700)*0.15 = 495.00
        """
        r = call(
            gain="100000",
            filing_status="married_joint",
            year=2025,
            term="long",
            magi="260000",
            apply_niit=True,
        )
        assert r["niit"] == "380.00"
        assert r["ltcg_tax"] == "495.00"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_negative_gain(self):
        with pytest.raises(InvalidInputError):
            call(gain="-1000", filing_status="single", year=2025, term="long")

    def test_invalid_term(self):
        with pytest.raises(InvalidInputError):
            call(gain="1000", filing_status="single", year=2025, term="medium")

    def test_invalid_filing_status(self):
        with pytest.raises(InvalidInputError):
            call(gain="1000", filing_status="xx", year=2025, term="long")

    def test_negative_magi(self):
        with pytest.raises(InvalidInputError):
            call(
                gain="1000", filing_status="single", year=2025,
                term="long", magi="-100", apply_niit=True,
            )

    def test_trace_and_policy_version(self):
        r = call(gain="100000", filing_status="single", year=2025, term="long")
        assert r["trace"]["tool"] == "tax_us.capital_gains"
        assert r["policy_version"]["year"] == 2025


class TestBatchRaceFree:
    def test_batch_100_parallel(self):
        """Run tax_us.capital_gains in 100 parallel core.batch calls."""
        from sootool.core.batch import BatchExecutor
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"cg-{i}",
                "tool": "tax_us.capital_gains",
                "args": {
                    "gain":          "100000",
                    "filing_status": "single",
                    "year":          2025,
                    "term":          "long",
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        first = response["results"][0]["result"]
        for entry in response["results"][1:]:
            assert entry["result"]["tax"] == first["tax"]
