"""Tests for engineering.si_prefix_convert tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestSiPrefixConvert:
    def test_si_mega_to_milli(self) -> None:
        """1 mega → milli: 10^(6 − (−3)) = 10^9 = 1_000_000_000."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="mega",
            to_prefix="milli",
        )
        assert Decimal(result["value"]) == Decimal("1000000000")
        assert "trace" in result

    def test_si_same_prefix_identity(self) -> None:
        """5 kilo → kilo = 5 (identity, exponent delta = 0)."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="5",
            from_prefix="kilo",
            to_prefix="kilo",
        )
        assert Decimal(result["value"]) == Decimal("5")

    def test_si_kilo_to_base(self) -> None:
        """3.5 kilo → base: 3.5 × 10^3 = 3500."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="3.5",
            from_prefix="kilo",
            to_prefix="",
        )
        assert Decimal(result["value"]) == Decimal("3500")

    def test_si_milli_to_micro(self) -> None:
        """1 milli → micro: 10^(−3 − (−6)) = 10^3 = 1000."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="milli",
            to_prefix="micro",
        )
        assert Decimal(result["value"]) == Decimal("1000")

    def test_si_giga_to_kilo(self) -> None:
        """1 giga → kilo: 10^(9−3) = 10^6 = 1_000_000."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="giga",
            to_prefix="kilo",
        )
        assert Decimal(result["value"]) == Decimal("1000000")

    def test_si_nano_to_pico(self) -> None:
        """1 nano → pico: 10^(−9 − (−12)) = 10^3 = 1000."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="nano",
            to_prefix="pico",
        )
        assert Decimal(result["value"]) == Decimal("1000")

    def test_si_tera_to_mega(self) -> None:
        """1 tera → mega: 10^(12−6) = 10^6 = 1_000_000."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="tera",
            to_prefix="mega",
        )
        assert Decimal(result["value"]) == Decimal("1000000")

    def test_si_case_insensitive(self) -> None:
        """Prefix lookup should be case-insensitive."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="MEGA",
            to_prefix="MILLI",
        )
        assert Decimal(result["value"]) == Decimal("1000000000")

    def test_si_unknown_prefix_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.si_prefix_convert",
                value="1",
                from_prefix="quecto",  # not in SI_PREFIXES dict
                to_prefix="kilo",
            )

    def test_si_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="1",
            from_prefix="kilo",
            to_prefix="base",
        )
        trace = result["trace"]
        assert trace["tool"] == "engineering.si_prefix_convert"
        assert "inputs" in trace
        assert "steps" in trace

    def test_si_fractional_value(self) -> None:
        """2.5 mega → kilo: 10^(6−3)=1000, result=2500."""
        result = REGISTRY.invoke(
            "engineering.si_prefix_convert",
            value="2.5",
            from_prefix="mega",
            to_prefix="kilo",
        )
        assert Decimal(result["value"]) == Decimal("2500")
