"""Tests for tax_us.capital_gains tool (LTCG + NIIT).

기대값은 Form 1040 Qualified Dividends and Capital Gain Tax Worksheet(2025) 의 줄 단위
계산, Rev. Proc. 2024-40 sec. 2.03, Rev. Proc. 2025-32 sec. 4.03, IRC 1411 에서 직접 구한다.

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
        """일반소득 없음: 1192.50 + 12% x (48475-11925) + 22% x (50000-48475) = 5914.00."""
        r = call(gain="50000", filing_status="single", year=2025, term="short")
        assert r["tax"] == "5914.00"
        assert r["term"] == "short"

    def test_short_with_ordinary_income(self):
        """단기 양도소득은 일반소득 위에 쌓인 증분 세액이다.

        tax(60000) - tax(50000) = 8114.00 - 5914.00 = 2200.00
        (tax(60000) = 5578.50 + 22% x (60000-48475) = 8114.00)
        """
        r = call(
            gain="10000",
            filing_status="single",
            year=2025,
            term="short",
            ordinary_taxable_income="50000",
        )
        assert r["tax"] == "2200.00"
        assert r["marginal_rate"] == "0.22"
        assert r["method"] == "ordinary_rates"


# ---------------------------------------------------------------------------
# Long-term gains stacked on ordinary taxable income (IRC 1(h)(1), QDCG worksheet)
# ---------------------------------------------------------------------------

class TestLTCGStacking:
    def test_partial_zero_band(self):
        """single 2025, 일반소득 40000, 양도 20000 (과세표준 60000).

        line 9 = min(60000, 48350) - min(40000, 48350) = 8350 (0%)
        line 17 = 20000 - 8350 = 11650 (15%) -> 1747.50
        """
        r = call(
            gain="20000", filing_status="single", year=2025, term="long",
            ordinary_taxable_income="40000",
        )
        assert r["ltcg_tax"] == "1747.50"
        assert r["tax"] == "1747.50"
        assert r["taxable_income"] == "60000"
        assert r["method"] == "qdcg_worksheet"

    def test_high_earner_no_zero_band(self):
        """일반소득 600000 > 533400: 0% 와 15% 여유분이 없어 전액 20% = 20000.00."""
        r = call(
            gain="100000", filing_status="single", year=2025, term="long",
            ordinary_taxable_income="600000",
        )
        assert r["tax"] == "20000.00"
        assert Decimal(r["marginal_rate"]) == Decimal("0.20")

    def test_straddle_15_and_20(self):
        """일반소득 500000, 양도 100000: 15% x 33400 + 20% x 66600 = 5010 + 13320 = 18330.00."""
        r = call(
            gain="100000", filing_status="single", year=2025, term="long",
            ordinary_taxable_income="500000",
        )
        assert r["tax"] == "18330.00"

    def test_mfj_zero_band_room(self):
        """MFJ 2025, 일반소득 80000, 양도 30000: 0% 16700, 15% x 13300 = 1995.00."""
        r = call(
            gain="30000", filing_status="married_joint", year=2025, term="long",
            ordinary_taxable_income="80000",
        )
        assert r["tax"] == "1995.00"

    def test_regular_tax_lower_line_25(self):
        """QDCG 워크시트 line 25: 일반 세율표 세액이 더 작으면 그 값을 쓴다.

        일반소득 48350, 양도 125 (single 2025): 15% 세액 18.75,
        일반 세율표 증분 tax(48475) - tax(48350) = 12% x 125 = 15.00.
        """
        r = call(
            gain="125", filing_status="single", year=2025, term="long",
            ordinary_taxable_income="48350",
        )
        assert r["tax"] == "15.00"
        assert r["method"] == "regular_tax"

    def test_negative_ordinary_income_rejected(self):
        with pytest.raises(InvalidInputError):
            call(
                gain="1000", filing_status="single", year=2025, term="long",
                ordinary_taxable_income="-1",
            )


# ---------------------------------------------------------------------------
# Tax year 2026 thresholds (Rev. Proc. 2025-32 sec. 4.03)
# ---------------------------------------------------------------------------

class TestLTCG2026:
    @pytest.mark.parametrize(
        ("filing_status", "zero_max"),
        [
            ("single",            "49450"),
            ("married_joint",     "98900"),
            ("married_separate",  "49450"),
            ("head_of_household", "66200"),
        ],
    )
    def test_zero_rate_maximum(self, filing_status, zero_max):
        r = call(gain=zero_max, filing_status=filing_status, year=2026, term="long")
        assert r["tax"] == "0.00"

    def test_single_15_pct(self):
        """(100000-49450) x 0.15 = 7582.50."""
        r = call(gain="100000", filing_status="single", year=2026, term="long")
        assert r["tax"] == "7582.50"

    @pytest.mark.parametrize(
        ("filing_status", "fifteen_max", "expected"),
        [
            # (15% 최대 적용액 - 0% 최대 적용액) x 0.15
            ("single",            "545500", "74407.50"),
            ("married_joint",     "613700", "77220.00"),
            ("married_separate",  "306850", "38610.00"),
            ("head_of_household", "579600", "77010.00"),
        ],
    )
    def test_fifteen_rate_maximum(self, filing_status, fifteen_max, expected):
        r = call(gain=fifteen_max, filing_status=filing_status, year=2026, term="long")
        assert r["tax"] == expected
        assert r["marginal_rate"] == "0.15"


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


class TestNIITDefaults:
    def test_magi_defaults_to_total_taxable_income(self):
        """magi 미지정: 일반소득 250000 + 양도 50000 = 300000 을 MAGI 하한으로 쓴다.

        excess = 300000 - 200000 = 100000; base = min(50000, 100000); niit = 1900.00
        LTCG: 일반소득이 533400 미만이므로 50000 전액 15% = 7500.00
        """
        r = call(
            gain="50000", filing_status="single", year=2025, term="long",
            ordinary_taxable_income="250000", apply_niit=True,
        )
        assert r["niit"] == "1900.00"
        assert r["ltcg_tax"] == "7500.00"
        assert r["tax"] == "9400.00"

    def test_surviving_spouse_joint_threshold(self):
        """IRC 1411(b)(1): 생존 배우자 임계액 250000. MAGI 260000, 양도 100000 -> 380.00."""
        r = call(
            gain="100000", filing_status="qualifying_surviving_spouse", year=2025,
            term="long", magi="260000", apply_niit=True,
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
