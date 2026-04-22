"""Tests for units.fx_convert and units.fx_triangulate currency tools."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.units  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestFxConvert:
    def test_fx_krw_to_usd(self) -> None:
        """1,000,000 KRW at 0.00075 → 750.00 USD (2 decimals)."""
        result = REGISTRY.invoke(
            "units.fx_convert",
            amount="1000000",
            from_ccy="KRW",
            to_ccy="USD",
            rate="0.00075",
        )
        assert result["amount"] == "750.00"
        assert result["currency"] == "USD"
        assert "trace" in result

    def test_fx_usd_to_jpy_no_decimal(self) -> None:
        """100 USD at 150 → 15000 JPY (0 decimals, no fractional yen)."""
        result = REGISTRY.invoke(
            "units.fx_convert",
            amount="100",
            from_ccy="USD",
            to_ccy="JPY",
            rate="150",
        )
        assert result["amount"] == "15000"
        assert result["currency"] == "JPY"

    def test_fx_usd_to_kwd_three_decimals(self) -> None:
        """1 USD at 0.307 → 0.307 KWD (3 decimals)."""
        result = REGISTRY.invoke(
            "units.fx_convert",
            amount="1",
            from_ccy="USD",
            to_ccy="KWD",
            rate="0.307",
        )
        assert len(result["amount"].split(".")[-1]) == 3
        assert result["currency"] == "KWD"

    def test_fx_jpy_rounding_half_even(self) -> None:
        """JPY result is integer (0 decimals) regardless of intermediate decimal."""
        result = REGISTRY.invoke(
            "units.fx_convert",
            amount="3",
            from_ccy="USD",
            to_ccy="JPY",
            rate="150.7",
            rounding="HALF_EVEN",
        )
        # 3 * 150.7 = 452.1 → rounds to 452 (JPY has 0 decimals)
        assert "." not in result["amount"]

    def test_fx_zero_rate_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.fx_convert",
                amount="100",
                from_ccy="USD",
                to_ccy="JPY",
                rate="0",
            )

    def test_fx_negative_amount_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.fx_convert",
                amount="-100",
                from_ccy="USD",
                to_ccy="JPY",
                rate="150",
            )

    def test_fx_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "units.fx_convert",
            amount="1000",
            from_ccy="USD",
            to_ccy="EUR",
            rate="0.92",
        )
        trace = result["trace"]
        assert trace["tool"] == "units.fx_convert"
        assert "inputs" in trace

    def test_fx_unknown_currency_uses_default_2_decimals(self) -> None:
        """Unknown currency code falls back to 2 decimal places."""
        result = REGISTRY.invoke(
            "units.fx_convert",
            amount="1",
            from_ccy="USD",
            to_ccy="XYZ",
            rate="1.0",
        )
        assert len(result["amount"].split(".")[-1]) == 2


class TestFxTriangulate:
    def test_fx_triangulate_krw_to_jpy_via_usd(self) -> None:
        """1,000,000 KRW * 0.00075 (→ USD) * 150 (→ JPY) = 112,500 JPY."""
        result = REGISTRY.invoke(
            "units.fx_triangulate",
            amount="1000000",
            from_ccy="KRW",
            via_ccy="USD",
            to_ccy="JPY",
            rate1="0.00075",
            rate2="150",
        )
        assert result["amount"] == "112500"
        assert result["currency"] == "JPY"
        assert "trace" in result

    def test_fx_triangulate_usd_to_eur_via_gbp(self) -> None:
        """100 USD * 0.8 (→ GBP) * 1.15 (→ EUR) = 92 EUR."""
        result = REGISTRY.invoke(
            "units.fx_triangulate",
            amount="100",
            from_ccy="USD",
            via_ccy="GBP",
            to_ccy="EUR",
            rate1="0.8",
            rate2="1.15",
        )
        assert Decimal(result["amount"]) == Decimal("92.00")

    def test_fx_triangulate_zero_rate1_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.fx_triangulate",
                amount="1000",
                from_ccy="KRW",
                via_ccy="USD",
                to_ccy="JPY",
                rate1="0",
                rate2="150",
            )

    def test_fx_triangulate_zero_rate2_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.fx_triangulate",
                amount="1000",
                from_ccy="KRW",
                via_ccy="USD",
                to_ccy="JPY",
                rate1="0.00075",
                rate2="0",
            )

    def test_units_batch_race_free(self) -> None:
        """units.fx_convert is race-condition-free under concurrent load."""
        def _call(i: int) -> dict:
            return REGISTRY.invoke(
                "units.fx_convert",
                amount=str(i * 1000),
                from_ccy="KRW",
                to_ccy="USD",
                rate="0.00075",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, i) for i in range(1, 33)]
            results = [f.result() for f in futures]

        for i, res in enumerate(results, start=1):
            expected = str((Decimal(str(i * 1000)) * Decimal("0.00075")).quantize(Decimal("0.01")))
            assert res["amount"] == expected, f"mismatch at i={i}"
