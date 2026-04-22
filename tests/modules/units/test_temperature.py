"""Tests for units.temperature scale conversion tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.units  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestTemperature:
    def test_temperature_c_to_f_boiling(self) -> None:
        """100°C (water boiling) → 212°F."""
        result = REGISTRY.invoke(
            "units.temperature", value="100", from_scale="C", to_scale="F"
        )
        assert Decimal(result["value"]) == Decimal("212")
        assert result["scale"] == "F"
        assert "trace" in result

    def test_temperature_f_to_c_freeze(self) -> None:
        """32°F (water freezing) → 0°C."""
        result = REGISTRY.invoke(
            "units.temperature", value="32", from_scale="F", to_scale="C"
        )
        assert Decimal(result["value"]) == Decimal("0")
        assert result["scale"] == "C"

    def test_temperature_c_to_k(self) -> None:
        """0°C → 273.15 K."""
        result = REGISTRY.invoke(
            "units.temperature", value="0", from_scale="C", to_scale="K"
        )
        assert Decimal(result["value"]) == Decimal("273.15")
        assert result["scale"] == "K"

    def test_temperature_k_to_c(self) -> None:
        """273.15 K → 0°C."""
        result = REGISTRY.invoke(
            "units.temperature", value="273.15", from_scale="K", to_scale="C"
        )
        assert abs(Decimal(result["value"])) < Decimal("1E-10")

    def test_temperature_f_to_k(self) -> None:
        """212°F → 373.15 K (boiling point)."""
        result = REGISTRY.invoke(
            "units.temperature", value="212", from_scale="F", to_scale="K"
        )
        assert abs(Decimal(result["value"]) - Decimal("373.15")) < Decimal("1E-10")

    def test_temperature_c_to_r(self) -> None:
        """0°C → 491.67 R."""
        result = REGISTRY.invoke(
            "units.temperature", value="0", from_scale="C", to_scale="R"
        )
        assert abs(Decimal(result["value"]) - Decimal("491.67")) < Decimal("1E-10")

    def test_temperature_r_to_k(self) -> None:
        """491.67 R → 273.15 K."""
        result = REGISTRY.invoke(
            "units.temperature", value="491.67", from_scale="R", to_scale="K"
        )
        assert abs(Decimal(result["value"]) - Decimal("273.15")) < Decimal("1E-5")

    def test_temperature_identity_c(self) -> None:
        """Same scale returns same value."""
        result = REGISTRY.invoke(
            "units.temperature", value="25", from_scale="C", to_scale="C"
        )
        assert Decimal(result["value"]) == Decimal("25")

    def test_temperature_unknown_from_scale_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.temperature", value="100", from_scale="X", to_scale="C"
            )

    def test_temperature_unknown_to_scale_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.temperature", value="100", from_scale="C", to_scale="Y"
            )

    def test_temperature_below_absolute_zero_raises(self) -> None:
        """Below absolute zero (< -273.15°C) must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.temperature", value="-274", from_scale="C", to_scale="K"
            )

    def test_temperature_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "units.temperature", value="100", from_scale="C", to_scale="F"
        )
        assert result["trace"]["tool"] == "units.temperature"
        assert "inputs" in result["trace"]

    def test_temperature_body_temp_c_to_f(self) -> None:
        """37°C (body temp) → 98.6°F."""
        result = REGISTRY.invoke(
            "units.temperature", value="37", from_scale="C", to_scale="F"
        )
        assert abs(Decimal(result["value"]) - Decimal("98.6")) < Decimal("1E-10")
