"""Tests for tax.progressive tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401 - registers tools
from sootool.core.errors   import InvalidInputError
from sootool.core.registry import REGISTRY


def call_progressive(**kwargs):
    return REGISTRY.invoke("tax.progressive", **kwargs)


THREE_BRACKET = [
    {"upper": "14000000",  "rate": "0.06"},
    {"upper": "50000000",  "rate": "0.15"},
    {"upper": None,        "rate": "0.24"},
]


class TestProgressiveBoundary:
    def test_boundary_exact_upper_inclusive(self):
        """Income == upper of first bracket → taxed entirely within that bracket."""
        result = call_progressive(
            taxable_income="14000000",
            brackets=THREE_BRACKET,
        )
        # 14_000_000 * 0.06 = 840_000
        assert result["tax"] == "840000"
        assert result["marginal_rate"] == "0.06"

    def test_boundary_one_above_upper(self):
        """Income = upper + 1 → spills into second bracket (marginal rate changes)."""
        result = call_progressive(
            taxable_income="14000001",
            brackets=THREE_BRACKET,
        )
        # 14_000_000 * 0.06 + 1 * 0.15 = 840_000 + 0.15 → rounds to 840_000 (integer)
        # The marginal rate shifts to 0.15 even though rounded tax is same
        assert result["marginal_rate"] == "0.15"
        # With decimals=2, the difference is visible
        result2 = call_progressive(
            taxable_income="14000001",
            brackets=THREE_BRACKET,
            decimals=2,
        )
        from decimal import Decimal
        assert Decimal(result2["tax"]) > Decimal("840000")

    def test_zero_income(self):
        result = call_progressive(
            taxable_income="0",
            brackets=THREE_BRACKET,
        )
        assert result["tax"] == "0"
        assert result["effective_rate"] == "0"

    def test_progressive_sample_50M(self):
        """14M*0.06 + 36M*0.15 = 840_000 + 5_400_000 = 6_240_000."""
        result = call_progressive(
            taxable_income="50000000",
            brackets=THREE_BRACKET,
        )
        assert result["tax"] == "6240000"

    def test_effective_rate_50M(self):
        result = call_progressive(
            taxable_income="50000000",
            brackets=THREE_BRACKET,
        )
        eff = Decimal(result["effective_rate"])
        # 6_240_000 / 50_000_000 = 0.1248
        assert abs(eff - Decimal("0.1248")) < Decimal("0.0001")

    def test_top_bracket_applied(self):
        """Income = 100M → top bracket (24%) kicks in above 50M."""
        result = call_progressive(
            taxable_income="100000000",
            brackets=THREE_BRACKET,
        )
        # 840_000 + 5_400_000 + 50_000_000*0.24 = 840_000+5_400_000+12_000_000 = 18_240_000
        assert result["tax"] == "18240000"
        assert result["marginal_rate"] == "0.24"

    def test_breakdown_structure(self):
        result = call_progressive(
            taxable_income="30000000",
            brackets=THREE_BRACKET,
        )
        bd = result["breakdown"]
        assert len(bd) == 3
        # First bracket: 14M * 6% = 840_000
        assert bd[0]["tax_in_bracket"] == "840000.00" or Decimal(bd[0]["tax_in_bracket"]) == Decimal("840000")

    def test_rounding_half_up(self):
        """Fractional tax should be rounded HALF_UP."""
        result = call_progressive(
            taxable_income="1",
            brackets=[{"upper": None, "rate": "0.055"}],
        )
        # 1 * 0.055 = 0.055 → HALF_UP → 0
        assert result["tax"] == "0"

    def test_decimals_2(self):
        result = call_progressive(
            taxable_income="1",
            brackets=[{"upper": None, "rate": "0.055"}],
            decimals=2,
        )
        assert result["tax"] == "0.06"


class TestProgressiveValidation:
    def test_invalid_rounding(self):
        with pytest.raises(InvalidInputError):
            call_progressive(
                taxable_income="1000000",
                brackets=THREE_BRACKET,
                rounding="INVALID",
            )

    def test_negative_income(self):
        with pytest.raises(InvalidInputError):
            call_progressive(
                taxable_income="-1",
                brackets=THREE_BRACKET,
            )

    def test_empty_brackets(self):
        with pytest.raises(InvalidInputError):
            call_progressive(taxable_income="1000000", brackets=[])

    def test_missing_top_null_bracket(self):
        with pytest.raises(InvalidInputError):
            call_progressive(
                taxable_income="1000000",
                brackets=[
                    {"upper": "10000000", "rate": "0.10"},
                    {"upper": "50000000", "rate": "0.20"},  # no null top
                ],
            )

    def test_non_ascending_brackets(self):
        with pytest.raises(InvalidInputError):
            call_progressive(
                taxable_income="1000000",
                brackets=[
                    {"upper": "50000000", "rate": "0.15"},
                    {"upper": "10000000", "rate": "0.06"},
                    {"upper": None,       "rate": "0.24"},
                ],
            )

    def test_null_not_last(self):
        with pytest.raises(InvalidInputError):
            call_progressive(
                taxable_income="1000000",
                brackets=[
                    {"upper": None,       "rate": "0.06"},
                    {"upper": "50000000", "rate": "0.15"},
                ],
            )


class TestProgressiveConcurrency:
    def test_batch_race_free(self):
        """100 parallel calls must yield identical results."""
        def run(_):
            return call_progressive(
                taxable_income="50000000",
                brackets=THREE_BRACKET,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(run, range(100)))

        taxes = [r["tax"] for r in results]
        assert len(set(taxes)) == 1, f"Non-deterministic results: {set(taxes)}"
