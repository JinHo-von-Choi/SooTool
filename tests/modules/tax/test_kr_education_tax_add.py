"""Tests for tax.kr_education_tax_add."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_education_tax_add", **kwargs)


class TestEducationTaxBasic:
    def test_20_percent_default_rate(self):
        r = call(base_tax="1000000")
        assert Decimal(r["education_tax"]) == Decimal("200000")
        assert Decimal(r["rate"]) == Decimal("0.20")

    def test_custom_rate(self):
        r = call(base_tax="1000000", rate="0.40")
        assert Decimal(r["education_tax"]) == Decimal("400000")

    def test_rounding_down_default(self):
        r = call(base_tax="12347")
        # 12347 * 0.20 = 2469.4 → DOWN → 2469
        assert Decimal(r["education_tax"]) == Decimal("2469")

    def test_zero_base(self):
        r = call(base_tax="0")
        assert Decimal(r["education_tax"]) == Decimal("0")

    def test_trace_present(self):
        r = call(base_tax="500000")
        assert r["trace"]["tool"] == "tax.kr_education_tax_add"


class TestEducationTaxValidation:
    def test_negative_base_raises(self):
        with pytest.raises(InvalidInputError):
            call(base_tax="-1")

    def test_negative_rate_raises(self):
        with pytest.raises(InvalidInputError):
            call(base_tax="100", rate="-0.1")

    def test_rate_above_one_raises(self):
        with pytest.raises(InvalidInputError):
            call(base_tax="100", rate="1.5")

    def test_invalid_rounding_raises(self):
        with pytest.raises(InvalidInputError):
            call(base_tax="100", rounding="UNKNOWN")

    def test_negative_decimals_raises(self):
        with pytest.raises(InvalidInputError):
            call(base_tax="100", decimals=-1)


class TestEducationTaxBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"edu-{i}",
                "tool": "tax.kr_education_tax_add",
                "args": {"base_tax": "500000"},
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        for r in results:
            assert r["education_tax"] == "100000"
