"""Tests for engineering electrical tools: Ohm's law, power, resistor networks."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestElectricalOhm:
    def test_ohm_v_from_ir(self) -> None:
        """I=2, R=5 → V=10."""
        result = REGISTRY.invoke(
            "engineering.electrical_ohm", current="2", resistance="5"
        )
        assert Decimal(result["voltage"]) == Decimal("10")
        assert result["current"] == "2"
        assert result["resistance"] == "5"
        assert "trace" in result

    def test_ohm_i_from_vr(self) -> None:
        """V=20, R=4 → I=5."""
        result = REGISTRY.invoke(
            "engineering.electrical_ohm", voltage="20", resistance="4"
        )
        assert Decimal(result["current"]) == Decimal("5")

    def test_ohm_r_from_vi(self) -> None:
        """V=12, I=3 → R=4."""
        result = REGISTRY.invoke(
            "engineering.electrical_ohm", voltage="12", current="3"
        )
        assert Decimal(result["resistance"]) == Decimal("4")

    def test_ohm_overdetermined_raises(self) -> None:
        """Providing all three values must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.electrical_ohm",
                voltage="10",
                current="2",
                resistance="5",
            )

    def test_ohm_underdetermined_raises(self) -> None:
        """Providing only one value must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("engineering.electrical_ohm", voltage="10")

    def test_ohm_zero_resistance_raises(self) -> None:
        """R=0 must raise when computing V = I*R (R must be > 0)."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.electrical_ohm", current="2", resistance="0"
            )

    def test_ohm_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "engineering.electrical_ohm", current="1", resistance="10"
        )
        assert result["trace"]["tool"] == "engineering.electrical_ohm"
        assert "inputs" in result["trace"]


class TestElectricalPower:
    def test_power_p_from_vi(self) -> None:
        """V=10, I=2 → P=20."""
        result = REGISTRY.invoke(
            "engineering.electrical_power", voltage="10", current="2"
        )
        assert Decimal(result["power"]) == Decimal("20")
        assert "trace" in result

    def test_power_p_from_i2r(self) -> None:
        """I=2, R=5 → P=20 (P=I²R)."""
        result = REGISTRY.invoke(
            "engineering.electrical_power", current="2", resistance="5"
        )
        assert Decimal(result["power"]) == Decimal("20")
        assert Decimal(result["voltage"]) == Decimal("10")

    def test_power_p_from_v2r(self) -> None:
        """V=10, R=5 → P=20 (P=V²/R)."""
        result = REGISTRY.invoke(
            "engineering.electrical_power", voltage="10", resistance="5"
        )
        assert Decimal(result["power"]) == Decimal("20")

    def test_power_vi_from_p_r(self) -> None:
        """P=20, R=5 → I=2, V=10 (I=√(P/R), V=√(P*R))."""
        result = REGISTRY.invoke(
            "engineering.electrical_power", power="20", resistance="5"
        )
        assert abs(Decimal(result["current"]) - Decimal("2")) < Decimal("1E-15")
        assert abs(Decimal(result["voltage"]) - Decimal("10")) < Decimal("1E-15")

    def test_power_overdetermined_raises(self) -> None:
        """Providing all 4 values must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.electrical_power",
                power="20",
                voltage="10",
                current="2",
                resistance="5",
            )

    def test_power_underdetermined_raises(self) -> None:
        """Providing only one value must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("engineering.electrical_power", power="20")

    def test_power_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "engineering.electrical_power", voltage="5", current="4"
        )
        assert result["trace"]["tool"] == "engineering.electrical_power"


class TestResistorSeries:
    def test_resistor_series(self) -> None:
        """[10, 20, 30] → total=60."""
        result = REGISTRY.invoke("engineering.resistor_series", resistors=["10", "20", "30"])
        assert Decimal(result["total"]) == Decimal("60")
        assert "trace" in result

    def test_resistor_series_single(self) -> None:
        """Single resistor → same value."""
        result = REGISTRY.invoke("engineering.resistor_series", resistors=["47"])
        assert Decimal(result["total"]) == Decimal("47")

    def test_resistor_series_decimal_values(self) -> None:
        """[4.7, 2.2, 10] → 16.9."""
        result = REGISTRY.invoke("engineering.resistor_series", resistors=["4.7", "2.2", "10"])
        assert abs(Decimal(result["total"]) - Decimal("16.9")) < Decimal("1E-20")

    def test_resistor_series_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("engineering.resistor_series", resistors=[])

    def test_resistor_series_zero_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("engineering.resistor_series", resistors=["10", "0", "5"])


class TestResistorParallel:
    def test_resistor_parallel_two_equal(self) -> None:
        """[10, 10] → total=5 (two equal resistors in parallel)."""
        result = REGISTRY.invoke("engineering.resistor_parallel", resistors=["10", "10"])
        assert Decimal(result["total"]) == Decimal("5")
        assert "trace" in result

    def test_resistor_parallel_three(self) -> None:
        """[6, 3, 2] → 1/(1/6+1/3+1/2) = 1."""
        result = REGISTRY.invoke("engineering.resistor_parallel", resistors=["6", "3", "2"])
        assert abs(Decimal(result["total"]) - Decimal("1")) < Decimal("1E-20")

    def test_resistor_parallel_single(self) -> None:
        """Single resistor parallel → same value."""
        result = REGISTRY.invoke("engineering.resistor_parallel", resistors=["100"])
        assert Decimal(result["total"]) == Decimal("100")

    def test_resistor_parallel_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("engineering.resistor_parallel", resistors=[])

    def test_engineering_batch_race_free(self) -> None:
        """engineering.resistor_series is race-condition-free under concurrent load."""
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.resistor_series",
                resistors=[str(i) for i in range(1, n + 1)],
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 33)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            expected = Decimal(n * (n + 1)) / Decimal("2")
            assert Decimal(res["total"]) == expected, f"mismatch at n={n}"
