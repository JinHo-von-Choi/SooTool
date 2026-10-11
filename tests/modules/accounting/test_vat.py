"""Tests for accounting VAT tools."""
from __future__ import annotations

from decimal import ROUND_UP, Decimal, localcontext

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestVatExtract:
    def test_vat_extract_11000(self) -> None:
        """gross=11000, rate=0.1, DOWN rounding -> net=10000, vat=1000"""
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="11000",
            rate="0.1",
            rounding="DOWN",
        )
        assert result["net"] == "10000"
        assert result["vat"] == "1000"
        assert "trace" in result

    def test_vat_extract_default_rate(self) -> None:
        """Default rate=0.1, DOWN. gross=22000 -> net=20000, vat=2000"""
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="22000",
            rate="0.1",
            rounding="DOWN",
        )
        assert result["net"] == "20000"
        assert result["vat"] == "2000"

    def test_vat_extract_non_round_gross(self) -> None:
        """gross=11001, rate=0.1, DOWN -> net=floor(11001/1.1)=10000, vat=1001"""
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="11001",
            rate="0.1",
            rounding="DOWN",
        )
        net = Decimal(result["net"])
        vat = Decimal(result["vat"])
        gross = Decimal("11001")
        # net + vat == gross
        assert net + vat == gross
        assert net >= Decimal("0")

    def test_vat_extract_trace(self) -> None:
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="5500",
            rate="0.1",
            rounding="DOWN",
        )
        assert result["trace"]["tool"] == "accounting.vat_extract"

    def test_vat_extract_half_up_rounding(self) -> None:
        result = REGISTRY.invoke(
            "accounting.vat_extract",
            gross="10500",
            rate="0.1",
            rounding="HALF_UP",
        )
        net = Decimal(result["net"])
        vat = Decimal(result["vat"])
        assert net + vat == Decimal("10500")


class TestVatAdd:
    def test_vat_add_10000(self) -> None:
        """net=10000, rate=0.1 -> gross=11000, vat=1000"""
        result = REGISTRY.invoke(
            "accounting.vat_add",
            net="10000",
            rate="0.1",
            rounding="HALF_EVEN",
        )
        assert result["gross"] == "11000"
        assert result["vat"] == "1000"
        assert "trace" in result

    def test_vat_add_default_rate(self) -> None:
        result = REGISTRY.invoke(
            "accounting.vat_add",
            net="50000",
            rate="0.1",
            rounding="HALF_EVEN",
        )
        assert result["gross"] == "55000"
        assert result["vat"] == "5000"

    def test_vat_add_trace(self) -> None:
        result = REGISTRY.invoke(
            "accounting.vat_add",
            net="3000",
            rate="0.1",
            rounding="HALF_EVEN",
        )
        assert result["trace"]["tool"] == "accounting.vat_add"

    def test_vat_add_non_integer_result(self) -> None:
        """net=3000, rate=0.15, HALF_EVEN -> vat=450, gross=3450"""
        result = REGISTRY.invoke(
            "accounting.vat_add",
            net="3000",
            rate="0.15",
            rounding="HALF_EVEN",
        )
        assert result["vat"] == "450"
        assert result["gross"] == "3450"


class TestVatAddPrecision:
    @pytest.mark.parametrize(
        ("net", "expected_vat", "expected_gross"),
        [("0", "0", "0"), ("5", "0", "5"), ("15", "2", "17")],
    )
    def test_zero_and_half_even_boundaries(self, net, expected_vat, expected_gross):
        result = REGISTRY.invoke("accounting.vat_add", net=net)
        assert result["vat"] == expected_vat
        assert result["gross"] == expected_gross

    @pytest.mark.parametrize("field", ["net", "rate"])
    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "bad", 0.1])
    def test_invalid_numbers(self, field, value):
        inputs = {"net": "100", "rate": "0.1", field: value}
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("accounting.vat_add", **inputs)

    @pytest.mark.parametrize(
        "inputs", [{"net": "-0.01"}, {"rate": "0"}, {"rate": "-0.1"}, {"rounding": "BAD"}],
    )
    def test_invalid_boundaries_and_policy(self, inputs):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("accounting.vat_add", **{"net": "100", **inputs})

    def test_large_amount_preserves_fraction_and_rounding(self):
        net = "1" + "0" * 60 + ".5"
        result = REGISTRY.invoke("accounting.vat_add", net=net, rate="1", rounding="HALF_UP")
        assert result["vat"] == "1" + "0" * 59 + "1"
        assert result["gross"] == "2" + "0" * 59 + "1.5"
        assert result["trace"]["output"] == {"gross": result["gross"], "vat": result["vat"]}

    def test_independent_of_caller_context(self):
        with localcontext() as context:
            context.prec = 6
            context.rounding = ROUND_UP
            result = REGISTRY.invoke("accounting.vat_add", net="1234567.89", rate="0.1")
            assert result["vat"] == "123457"
            assert result["gross"] == "1358024.89"
            assert context.prec == 6
            assert context.rounding == ROUND_UP

    def test_small_fraction_survives_adding_integer_vat(self):
        net = "1." + "0" * 59 + "1"
        result = REGISTRY.invoke("accounting.vat_add", net=net, rate="1")
        assert result["vat"] == "1"
        assert result["gross"] == "2." + "0" * 59 + "1"
