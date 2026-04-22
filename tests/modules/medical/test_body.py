"""Tests for medical body measurement tools (BMI, BSA)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.medical  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestBMI:
    def test_bmi_70kg_175cm(self) -> None:
        """70 kg / 1.75 m^2 = 22.857... -> 22.86, normal."""
        result = REGISTRY.invoke("medical.bmi", height_m="1.75", weight_kg="70")
        assert result["bmi"] == "22.86"
        assert result["category"] == "normal"
        assert "trace" in result

    def test_bmi_50kg_180cm(self) -> None:
        """50 kg / 1.80 m^2 = 15.432... -> 15.43, underweight."""
        result = REGISTRY.invoke("medical.bmi", height_m="1.80", weight_kg="50")
        assert result["bmi"] == "15.43"
        assert result["category"] == "underweight"

    def test_bmi_100kg_175cm(self) -> None:
        """100 kg / 1.75 m^2 = 32.653... -> 32.65, obese_1."""
        result = REGISTRY.invoke("medical.bmi", height_m="1.75", weight_kg="100")
        assert result["bmi"] == "32.65"
        assert result["category"] == "obese_1"

    def test_bmi_overweight_boundary(self) -> None:
        """BMI exactly 25.00 -> overweight."""
        # weight = 25 * h^2; h=1.0 -> weight=25
        result = REGISTRY.invoke("medical.bmi", height_m="1.0", weight_kg="25")
        assert result["bmi"] == "25.00"
        assert result["category"] == "overweight"

    def test_bmi_obese_2(self) -> None:
        result = REGISTRY.invoke("medical.bmi", height_m="1.6", weight_kg="100")
        bmi = Decimal(result["bmi"])
        assert bmi >= Decimal("35")
        assert result["category"] == "obese_2"

    def test_bmi_obese_3(self) -> None:
        result = REGISTRY.invoke("medical.bmi", height_m="1.5", weight_kg="100")
        bmi = Decimal(result["bmi"])
        assert bmi >= Decimal("40")
        assert result["category"] == "obese_3"

    def test_bmi_zero_height_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("medical.bmi", height_m="0", weight_kg="70")

    def test_bmi_negative_weight_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("medical.bmi", height_m="1.75", weight_kg="-1")

    def test_bmi_trace_structure(self) -> None:
        result = REGISTRY.invoke("medical.bmi", height_m="1.75", weight_kg="70")
        trace = result["trace"]
        assert trace["tool"] == "medical.bmi"
        assert "inputs" in trace
        assert "output" in trace


class TestBSA:
    def test_bsa_dubois_170_70(self) -> None:
        """DuBois BSA for h=170cm, w=70kg approx 1.81 m²."""
        result = REGISTRY.invoke(
            "medical.bsa", height_cm="170", weight_kg="70", method="dubois"
        )
        bsa = Decimal(result["bsa_m2"])
        assert abs(bsa - Decimal("1.81")) <= Decimal("0.02")
        assert "trace" in result

    def test_bsa_mosteller_170_70(self) -> None:
        """Mosteller BSA for h=170cm, w=70kg approx sqrt(170*70/3600) ~ 1.82 m²."""
        result = REGISTRY.invoke(
            "medical.bsa", height_cm="170", weight_kg="70", method="mosteller"
        )
        bsa = Decimal(result["bsa_m2"])
        # sqrt(170*70/3600) = sqrt(11900/3600) = sqrt(3.305...) ~ 1.8179
        assert abs(bsa - Decimal("1.82")) <= Decimal("0.02")

    def test_bsa_dubois_default_method(self) -> None:
        """Default method is dubois."""
        result = REGISTRY.invoke(
            "medical.bsa", height_cm="170", weight_kg="70"
        )
        assert "bsa_m2" in result

    def test_bsa_invalid_method_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.bsa", height_cm="170", weight_kg="70", method="invalid"
            )

    def test_bsa_zero_height_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("medical.bsa", height_cm="0", weight_kg="70")

    def test_bsa_four_decimal_places(self) -> None:
        result = REGISTRY.invoke(
            "medical.bsa", height_cm="170", weight_kg="70", method="dubois"
        )
        # Result should have at most 4 decimal places
        bsa_str = result["bsa_m2"]
        parts = bsa_str.split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 4
