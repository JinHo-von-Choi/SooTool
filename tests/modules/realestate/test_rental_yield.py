"""Tests for rental yield calculator."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
import sootool.server  # noqa: F401  — registers core.batch
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestRentalYield:
    def test_rental_yield_gross_simple(self) -> None:
        """rent=50M, price=1B -> 5.00%."""
        result = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
        )
        assert result["yield_pct"] == "5.00"
        assert "trace" in result

    def test_rental_yield_net(self) -> None:
        """rent=50M, price=1B, expenses=10M -> net=(40M/1B)*100=4.00%."""
        result = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
            annual_expenses="10000000",
            yield_type="net",
        )
        assert result["yield_pct"] == "4.00"

    def test_rental_yield_gross_ignores_expenses(self) -> None:
        """Gross yield ignores annual_expenses."""
        result_no_exp = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
            yield_type="gross",
        )
        result_with_exp = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="50000000",
            property_price="1000000000",
            annual_expenses="10000000",
            yield_type="gross",
        )
        assert result_no_exp["yield_pct"] == result_with_exp["yield_pct"]

    def test_rental_yield_custom_decimals(self) -> None:
        result = REGISTRY.invoke(
            "realestate.rental_yield",
            annual_rent="33333333",
            property_price="1000000000",
            decimals=4,
        )
        assert len(result["yield_pct"].split(".")[1]) <= 4

    def test_rental_yield_invalid_type_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.rental_yield",
                annual_rent="50000000",
                property_price="1000000000",
                yield_type="invalid",
            )

    def test_rental_yield_zero_price_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.rental_yield",
                annual_rent="50000000",
                property_price="0",
            )

    def test_rental_yield_negative_expenses_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.rental_yield",
                annual_rent="50000000",
                property_price="1000000000",
                annual_expenses="-1",
                yield_type="net",
            )

    def test_realestate_batch_race_free(self) -> None:
        """Multiple realestate tools in batch -> deterministic results."""
        items = [
            {
                "tool": "realestate.rental_yield",
                "args": {
                    "annual_rent":    "50000000",
                    "property_price": "1000000000",
                },
                "id": "yield1",
            },
            {
                "tool": "realestate.kr_dsr",
                "args": {
                    "annual_debt_payment": "3000000",
                    "annual_income":       "10000000",
                    "year":                2026,
                },
                "id": "dsr1",
            },
        ]
        batch_result = REGISTRY.invoke(
            "core.batch",
            items=items,
            deterministic=True,
        )
        results_map = {r["id"]: r for r in batch_result["results"]}
        assert results_map["yield1"]["result"]["yield_pct"] == "5.00"
        dsr = Decimal(results_map["dsr1"]["result"]["dsr"])
        assert abs(dsr - Decimal("0.30")) < Decimal("0.0001")
