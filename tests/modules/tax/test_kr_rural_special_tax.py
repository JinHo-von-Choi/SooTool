"""Tests for tax.kr_rural_special_tax."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_rural_special_tax", **kwargs)


class TestRuralSpecialTaxBasic:
    def test_base_mode_10_percent(self):
        r = call(amount="1000000", mode="base")
        assert Decimal(r["rural_special_tax"]) == Decimal("100000")
        assert Decimal(r["rate"]) == Decimal("0.10")

    def test_reduced_mode_20_percent(self):
        r = call(amount="1000000", mode="reduced")
        assert Decimal(r["rural_special_tax"]) == Decimal("200000")
        assert Decimal(r["rate"]) == Decimal("0.20")

    def test_rounding_down_default(self):
        r = call(amount="12345", mode="base")
        # 12345 * 0.10 = 1234.5 → DOWN → 1234
        assert Decimal(r["rural_special_tax"]) == Decimal("1234")

    def test_zero_amount(self):
        r = call(amount="0", mode="base")
        assert Decimal(r["rural_special_tax"]) == Decimal("0")

    def test_trace_present(self):
        r = call(amount="100000", mode="base")
        assert r["trace"]["tool"] == "tax.kr_rural_special_tax"
        assert r["mode"] == "base"


class TestRuralSpecialTaxValidation:
    def test_invalid_mode_raises(self):
        with pytest.raises(InvalidInputError):
            call(amount="100", mode="unknown")

    def test_negative_amount_raises(self):
        with pytest.raises(InvalidInputError):
            call(amount="-1", mode="base")

    def test_invalid_rounding_raises(self):
        with pytest.raises(InvalidInputError):
            call(amount="100", rounding="UNKNOWN")

    def test_negative_decimals_raises(self):
        with pytest.raises(InvalidInputError):
            call(amount="100", decimals=-1)

    def test_large_value_reduced(self):
        r = call(amount="50000000", mode="reduced")
        assert Decimal(r["rural_special_tax"]) == Decimal("10000000")


class TestRuralSpecialTaxBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"rst-{i}",
                "tool": "tax.kr_rural_special_tax",
                "args": {"amount": "300000", "mode": "base"},
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        for r in results:
            assert r["rural_special_tax"] == "30000"
