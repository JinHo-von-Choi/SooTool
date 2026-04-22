"""Tests for medical weight-based dose calculator."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.medical  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestDoseWeightBased:
    def test_dose_basic(self) -> None:
        """70kg * 5mg/kg = 350mg."""
        result = REGISTRY.invoke(
            "medical.dose_weight_based",
            weight_kg="70",
            dose_per_kg="5",
        )
        assert Decimal(result["dose"]) == Decimal("350")
        assert result["capped"] is False
        assert result["unit"] == "mg"
        assert "trace" in result

    def test_dose_capped(self) -> None:
        """100kg * 5mg/kg = 500, capped at 400."""
        result = REGISTRY.invoke(
            "medical.dose_weight_based",
            weight_kg="100",
            dose_per_kg="5",
            max_dose="400",
        )
        assert Decimal(result["dose"]) == Decimal("400")
        assert result["capped"] is True

    def test_dose_not_capped_when_below_max(self) -> None:
        """50kg * 5mg/kg = 250, max_dose=400 -> not capped."""
        result = REGISTRY.invoke(
            "medical.dose_weight_based",
            weight_kg="50",
            dose_per_kg="5",
            max_dose="400",
        )
        assert Decimal(result["dose"]) == Decimal("250")
        assert result["capped"] is False

    def test_dose_negative_weight_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.dose_weight_based",
                weight_kg="-1",
                dose_per_kg="5",
            )

    def test_dose_zero_weight(self) -> None:
        """Zero weight is valid (e.g., neonatal edge case before birth), dose=0."""
        result = REGISTRY.invoke(
            "medical.dose_weight_based",
            weight_kg="0",
            dose_per_kg="5",
        )
        assert Decimal(result["dose"]) == Decimal("0")
        assert result["capped"] is False

    def test_dose_custom_unit(self) -> None:
        result = REGISTRY.invoke(
            "medical.dose_weight_based",
            weight_kg="70",
            dose_per_kg="2",
            unit="mcg",
        )
        assert result["unit"] == "mcg"

    def test_dose_fractional(self) -> None:
        """0.5mg/kg * 70kg = 35."""
        result = REGISTRY.invoke(
            "medical.dose_weight_based",
            weight_kg="70",
            dose_per_kg="0.5",
        )
        assert Decimal(result["dose"]) == Decimal("35")

    def test_dose_negative_max_dose_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.dose_weight_based",
                weight_kg="70",
                dose_per_kg="5",
                max_dose="-1",
            )
