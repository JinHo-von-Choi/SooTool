"""Tests for extended unit conversions: energy, pressure, data size, small time."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.units  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestEnergy:
    def test_kwh_to_joule(self) -> None:
        r = REGISTRY.invoke(
            "units.energy_convert", magnitude="1", from_unit="kWh", to_unit="J",
        )
        assert Decimal(r["magnitude"]) == Decimal("3600000")

    def test_cal_to_joule(self) -> None:
        r = REGISTRY.invoke(
            "units.energy_convert", magnitude="1", from_unit="cal", to_unit="J",
        )
        assert Decimal(r["magnitude"]) == Decimal("4.184")

    def test_ev_to_joule(self) -> None:
        r = REGISTRY.invoke(
            "units.energy_convert", magnitude="1", from_unit="eV", to_unit="J",
        )
        assert abs(Decimal(r["magnitude"]) - Decimal("1.602176634E-19")) < Decimal("1E-25")

    def test_invalid_unit_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "units.energy_convert", magnitude="1", from_unit="foo", to_unit="J",
            )


class TestPressure:
    def test_atm_to_pa(self) -> None:
        r = REGISTRY.invoke(
            "units.pressure_convert", magnitude="1", from_unit="atm", to_unit="Pa",
        )
        assert Decimal(r["magnitude"]) == Decimal("101325")

    def test_bar_to_kpa(self) -> None:
        r = REGISTRY.invoke(
            "units.pressure_convert", magnitude="1", from_unit="bar", to_unit="kPa",
        )
        assert Decimal(r["magnitude"]) == Decimal("100")

    def test_psi_to_kpa(self) -> None:
        r = REGISTRY.invoke(
            "units.pressure_convert", magnitude="1", from_unit="psi", to_unit="kPa",
        )
        # 6.895 kPa
        assert abs(Decimal(r["magnitude"]) - Decimal("6.895")) < Decimal("0.005")


class TestDataSize:
    def test_si_mb_to_kb(self) -> None:
        r = REGISTRY.invoke(
            "units.data_size_convert", magnitude="1", from_unit="MB", to_unit="kB", mode="si",
        )
        assert Decimal(r["magnitude"]) == Decimal("1000")

    def test_iec_gib_to_mib(self) -> None:
        r = REGISTRY.invoke(
            "units.data_size_convert", magnitude="1", from_unit="GiB", to_unit="MiB", mode="iec",
        )
        assert Decimal(r["magnitude"]) == Decimal("1024")

    def test_mixed_mb_to_mib(self) -> None:
        # 1 MB = 1,000,000 B; MiB = 1,048,576 B → 1 MB = 0.9537 MiB
        r = REGISTRY.invoke(
            "units.data_size_convert", magnitude="1", from_unit="MB", to_unit="MiB", mode="mixed",
        )
        assert abs(Decimal(r["magnitude"]) - Decimal("0.9536743")) < Decimal("1E-6")

    def test_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "units.data_size_convert",
                magnitude="-1", from_unit="MB", to_unit="kB",
            )


class TestTimeSmall:
    def test_us_to_ns(self) -> None:
        r = REGISTRY.invoke(
            "units.time_small_convert", magnitude="1", from_unit="us", to_unit="ns",
        )
        assert Decimal(r["magnitude"]) == Decimal("1000")

    def test_ms_to_s(self) -> None:
        r = REGISTRY.invoke(
            "units.time_small_convert", magnitude="1000", from_unit="ms", to_unit="s",
        )
        assert Decimal(r["magnitude"]) == Decimal("1")


class TestBatchRaceFree:
    def test_energy_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "units.energy_convert", magnitude="1", from_unit="kWh", to_unit="J",
        )["magnitude"]

        def run() -> str:
            return REGISTRY.invoke(
                "units.energy_convert", magnitude="1", from_unit="kWh", to_unit="J",
            )["magnitude"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
