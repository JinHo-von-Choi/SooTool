"""Tests for tax.kr_local_income_tax."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_local_income_tax", **kwargs)


class TestLocalIncomeTaxBasic:
    def test_10_percent_rate(self):
        r = call(income_tax="1000000")
        assert Decimal(r["local_income_tax"]) == Decimal("100000")
        assert Decimal(r["rate"]) == Decimal("0.10")

    def test_rounding_down_default(self):
        r = call(income_tax="12345")
        # 12345 * 0.10 = 1234.5 → DOWN → 1234
        assert Decimal(r["local_income_tax"]) == Decimal("1234")

    def test_rounding_half_up_option(self):
        r = call(income_tax="12345", rounding="HALF_UP")
        assert Decimal(r["local_income_tax"]) == Decimal("1235")

    def test_zero_income_tax(self):
        r = call(income_tax="0")
        assert Decimal(r["local_income_tax"]) == Decimal("0")

    def test_trace_present(self):
        r = call(income_tax="500000")
        assert r["trace"]["tool"] == "tax.kr_local_income_tax"
        assert "formula" in r["trace"]


class TestLocalIncomeTaxValidation:
    def test_negative_raises(self):
        with pytest.raises(InvalidInputError):
            call(income_tax="-1")

    def test_invalid_rounding_raises(self):
        with pytest.raises(InvalidInputError):
            call(income_tax="1000", rounding="UNKNOWN")

    def test_negative_decimals_raises(self):
        with pytest.raises(InvalidInputError):
            call(income_tax="1000", decimals=-1)

    def test_large_value(self):
        r = call(income_tax="1000000000")  # 10억
        assert Decimal(r["local_income_tax"]) == Decimal("100000000")

    def test_decimals_precision(self):
        r = call(income_tax="12345", decimals=2, rounding="HALF_UP")
        assert Decimal(r["local_income_tax"]) == Decimal("1234.50")


class TestLocalIncomeTaxBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"loc-{i}",
                "tool": "tax.kr_local_income_tax",
                "args": {"income_tax": "2000000"},
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        for r in results:
            assert r["local_income_tax"] == "200000"
