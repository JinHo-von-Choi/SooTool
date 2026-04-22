"""Tests for units.convert physical unit conversion tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.units  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestConvert:
    def test_convert_meter_to_feet(self) -> None:
        """1 meter ≈ 3.28083... feet (pint reference value)."""
        result = REGISTRY.invoke("units.convert", magnitude="1", from_unit="meter", to_unit="foot")
        feet = Decimal(result["magnitude"])
        assert abs(feet - Decimal("3.28083989501312")) < Decimal("1E-10")
        assert result["unit"] == "foot"
        assert "trace" in result

    def test_convert_km_to_mile(self) -> None:
        """1 km ≈ 0.621371 mile."""
        result = REGISTRY.invoke("units.convert", magnitude="1", from_unit="kilometer", to_unit="mile")
        miles = Decimal(result["magnitude"])
        assert abs(miles - Decimal("0.621371")) < Decimal("1E-5")

    def test_convert_kg_to_gram(self) -> None:
        """2.5 kg = 2500 g."""
        result = REGISTRY.invoke("units.convert", magnitude="2.5", from_unit="kilogram", to_unit="gram")
        assert Decimal(result["magnitude"]) == Decimal("2500")

    def test_convert_liter_to_ml(self) -> None:
        """1 liter = 1000 ml."""
        result = REGISTRY.invoke("units.convert", magnitude="1", from_unit="liter", to_unit="milliliter")
        assert Decimal(result["magnitude"]) == Decimal("1000")

    def test_convert_incompatible_raises(self) -> None:
        """meter → second must raise InvalidInputError (dimensionally incompatible)."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("units.convert", magnitude="1", from_unit="meter", to_unit="second")

    def test_convert_unknown_unit_raises(self) -> None:
        """Unknown unit string raises InvalidInputError."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("units.convert", magnitude="1", from_unit="foobar", to_unit="meter")

    def test_convert_trace_structure(self) -> None:
        """Trace dict must contain expected keys."""
        result = REGISTRY.invoke("units.convert", magnitude="5", from_unit="meter", to_unit="meter")
        trace = result["trace"]
        assert trace["tool"] == "units.convert"
        assert "inputs" in trace
        assert "steps" in trace

    def test_convert_identity(self) -> None:
        """Converting to the same unit returns same magnitude."""
        result = REGISTRY.invoke("units.convert", magnitude="42", from_unit="meter", to_unit="meter")
        assert Decimal(result["magnitude"]) == Decimal("42")
