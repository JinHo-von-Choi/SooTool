"""Tests for payroll.kr_year_end_tax_settlement."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_year_end_tax_settlement", **kwargs)


class TestYearEndBasic:
    def test_60m_gross_underpaid_results_in_additional(self):
        r = call(annual_gross="60000000", prepaid_tax="3000000", year=2026)
        assert Decimal(r["labor_deduction"]) == Decimal("12750000.00")
        assert Decimal(r["taxable_income"])  == Decimal("45750000.00")
        assert Decimal(r["computed_tax"])    == Decimal("5602500")
        assert Decimal(r["decided_tax"])     == Decimal("5472500")
        assert r["status"] == "additional"
        assert Decimal(r["refund"]) < Decimal("0")

    def test_overpaid_refund(self):
        r = call(annual_gross="30000000", prepaid_tax="5000000", year=2026)
        assert r["status"] == "refund"
        assert Decimal(r["refund"]) > Decimal("0")

    def test_settled_exact(self):
        # run once, then set prepaid = decided to simulate settled
        r0 = call(annual_gross="40000000", prepaid_tax="0", year=2026)
        decided = r0["decided_tax"]
        r = call(annual_gross="40000000", prepaid_tax=decided, year=2026)
        assert r["status"] == "settled"
        assert Decimal(r["refund"]) == Decimal("0")

    def test_extra_credits_reduce_tax(self):
        r0 = call(annual_gross="60000000", prepaid_tax="0", year=2026)
        r1 = call(
            annual_gross="60000000", prepaid_tax="0", year=2026,
            extra_tax_credits="500000",
        )
        assert Decimal(r1["decided_tax"]) < Decimal(r0["decided_tax"])

    def test_policy_version_and_trace(self):
        r = call(annual_gross="30000000", prepaid_tax="500000", year=2026)
        assert r["trace"]["tool"] == "payroll.kr_year_end_tax_settlement"
        assert r["policy_version"]["year"] == 2026


class TestYearEndValidation:
    def test_negative_gross_raises(self):
        with pytest.raises(InvalidInputError):
            call(annual_gross="-1", prepaid_tax="0", year=2026)

    def test_zero_gross_yields_zero_tax(self):
        r = call(annual_gross="0", prepaid_tax="0", year=2026)
        assert Decimal(r["decided_tax"]) == Decimal("0")
        assert Decimal(r["taxable_income"]) == Decimal("0")

    def test_zero_dependents_raises(self):
        with pytest.raises(InvalidInputError):
            call(annual_gross="30000000", prepaid_tax="0", year=2026, dependents=0)

    def test_negative_prepaid_raises(self):
        with pytest.raises(InvalidInputError):
            call(annual_gross="30000000", prepaid_tax="-100", year=2026)

    def test_negative_extras_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                annual_gross="30000000", prepaid_tax="0", year=2026,
                extra_deductions="-1",
            )
        with pytest.raises(InvalidInputError):
            call(
                annual_gross="30000000", prepaid_tax="0", year=2026,
                extra_tax_credits="-1",
            )


class TestYearEndBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"ye-{i}",
                "tool": "payroll.kr_year_end_tax_settlement",
                "args": {
                    "annual_gross": "50000000",
                    "prepaid_tax":  "2500000",
                    "year":         2026,
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["decided_tax"] == first["decided_tax"]
            assert r["refund"] == first["refund"]
