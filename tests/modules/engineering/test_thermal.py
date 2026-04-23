"""Tests for engineering.thermal tools."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestFourierHeatConduction:
    def test_basic(self) -> None:
        """k=0.5, A=1, ΔT=100, L=0.1 → Q = 500 W."""
        r = REGISTRY.invoke(
            "engineering.fourier_heat_conduction",
            thermal_conductivity="0.5", area="1",
            temperature_hot="100", temperature_cold="0",
            thickness="0.1",
        )
        assert Decimal(r["heat_rate_w"]) == Decimal("500")

    def test_no_gradient_zero_flux(self) -> None:
        r = REGISTRY.invoke(
            "engineering.fourier_heat_conduction",
            thermal_conductivity="0.5", area="1",
            temperature_hot="25", temperature_cold="25",
            thickness="0.1",
        )
        assert Decimal(r["heat_rate_w"]) == Decimal("0")

    def test_reversed_temperatures_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.fourier_heat_conduction",
                thermal_conductivity="0.5", area="1",
                temperature_hot="0", temperature_cold="100",
                thickness="0.1",
            )

    def test_zero_thickness_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.fourier_heat_conduction",
                thermal_conductivity="0.5", area="1",
                temperature_hot="100", temperature_cold="0",
                thickness="0",
            )

    def test_zero_conductivity_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.fourier_heat_conduction",
                thermal_conductivity="0", area="1",
                temperature_hot="100", temperature_cold="0",
                thickness="0.1",
            )


class TestThermalResistance:
    def test_series(self) -> None:
        r = REGISTRY.invoke(
            "engineering.thermal_resistance",
            resistances=["1", "2", "3"], topology="series",
        )
        assert Decimal(r["total"]) == Decimal("6")

    def test_parallel(self) -> None:
        """Two 2 K/W in parallel → 1 K/W."""
        r = REGISTRY.invoke(
            "engineering.thermal_resistance",
            resistances=["2", "2"], topology="parallel",
        )
        _assert_close(r["total"], Decimal("1"))

    def test_single_passes_through(self) -> None:
        r = REGISTRY.invoke(
            "engineering.thermal_resistance",
            resistances=["5"], topology="series",
        )
        assert Decimal(r["total"]) == Decimal("5")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.thermal_resistance",
                resistances=[], topology="series",
            )

    def test_negative_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.thermal_resistance",
                resistances=["1", "-2"], topology="series",
            )

    def test_invalid_topology_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.thermal_resistance",
                resistances=["1", "2"], topology="weird",
            )


class TestStefanBoltzmann:
    def test_equal_temperatures_zero_heat(self) -> None:
        r = REGISTRY.invoke(
            "engineering.stefan_boltzmann",
            emissivity="1", area="1",
            temperature_surface="300", temperature_surround="300",
        )
        assert abs(Decimal(r["heat_rate_w"])) < Decimal("1E-10")

    def test_body_radiates_to_cold_surround(self) -> None:
        """ε=1, A=1, Ts=500, Tsurr=300 → Q = σ(500⁴ - 300⁴) ≈ 3084.68 W."""
        r = REGISTRY.invoke(
            "engineering.stefan_boltzmann",
            emissivity="1", area="1",
            temperature_surface="500", temperature_surround="300",
        )
        # σ = 5.670374419e-8 ; 500⁴ − 300⁴ = 6.25e10 − 8.1e9 = 5.44e10
        # Q = 5.670374419e-8 × 5.44e10 = 3084.6836839360.
        _assert_close(r["heat_rate_w"], Decimal("3084.683683936"), tol=Decimal("1E-6"))

    def test_emissivity_out_of_range_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.stefan_boltzmann",
                emissivity="1.5", area="1",
                temperature_surface="300", temperature_surround="300",
            )

    def test_zero_absolute_temperature_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.stefan_boltzmann",
                emissivity="1", area="1",
                temperature_surface="0", temperature_surround="300",
            )

    def test_zero_area_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.stefan_boltzmann",
                emissivity="1", area="0",
                temperature_surface="500", temperature_surround="300",
            )


class TestLmtd:
    def test_standard(self) -> None:
        """ΔT₁=30, ΔT₂=10 → LMTD = 20/ln(3) ≈ 18.2048."""
        r = REGISTRY.invoke(
            "engineering.lmtd",
            delta_t_hot_inlet="30", delta_t_cold_outlet="10",
        )
        _assert_close(r["lmtd"], Decimal("18.20478453"), tol=Decimal("1E-5"))

    def test_equal_delta_t_limit(self) -> None:
        """ΔT₁ == ΔT₂ → LMTD = ΔT₁ (analytic limit)."""
        r = REGISTRY.invoke(
            "engineering.lmtd",
            delta_t_hot_inlet="10", delta_t_cold_outlet="10",
        )
        assert Decimal(r["lmtd"]) == Decimal("10")

    def test_zero_delta_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.lmtd",
                delta_t_hot_inlet="0", delta_t_cold_outlet="10",
            )

    def test_negative_delta_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.lmtd",
                delta_t_hot_inlet="10", delta_t_cold_outlet="-5",
            )


class TestConvectiveHeatTransfer:
    def test_basic(self) -> None:
        """h=25, A=2, ΔT=30 → Q = 1500 W."""
        r = REGISTRY.invoke(
            "engineering.convective_heat_transfer",
            heat_transfer_coefficient="25", area="2",
            temperature_surface="50", temperature_fluid="20",
        )
        assert Decimal(r["heat_rate_w"]) == Decimal("1500")

    def test_negative_delta_t_negative_q(self) -> None:
        """Surface cooler than fluid → negative Q (heat flows into surface)."""
        r = REGISTRY.invoke(
            "engineering.convective_heat_transfer",
            heat_transfer_coefficient="25", area="2",
            temperature_surface="10", temperature_fluid="30",
        )
        assert Decimal(r["heat_rate_w"]) == Decimal("-1000")

    def test_zero_h_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.convective_heat_transfer",
                heat_transfer_coefficient="0", area="2",
                temperature_surface="50", temperature_fluid="20",
            )

    def test_zero_area_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.convective_heat_transfer",
                heat_transfer_coefficient="25", area="0",
                temperature_surface="50", temperature_fluid="20",
            )


class TestThermalConcurrency:
    def test_lmtd_batch_race_free(self) -> None:
        """engineering.lmtd thread-safe under N=100."""
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.lmtd",
                delta_t_hot_inlet=str(n + 10),
                delta_t_cold_outlet="5",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for res in results:
            assert Decimal(res["lmtd"]) > Decimal("0")


class TestRegistryCoverage:
    """Ensure all P4-M2 new tools are registered in REGISTRY."""

    _EXPECTED_NEW_TOOLS = [
        # electrical_ac
        "engineering.ac_impedance",
        "engineering.rlc_time_constant",
        "engineering.lc_resonant_frequency",
        "engineering.rc_filter_cutoff",
        "engineering.capacitor_combine",
        "engineering.inductor_combine",
        "engineering.three_phase_power",
        "engineering.power_factor_correction",
        "engineering.db_convert",
        "engineering.resistor_color_code",
        "engineering.opamp_gain",
        # mechanical
        "engineering.mech_stress",
        "engineering.mech_strain",
        "engineering.elastic_modulus_relate",
        "engineering.torque_rotational_power",
        "engineering.moment_of_inertia",
        # fluid extensions
        "engineering.bernoulli",
        "engineering.darcy_weisbach",
        "engineering.moody_friction_factor",
        "engineering.hazen_williams_flow",
        "engineering.pump_hydraulic_power",
        # thermal
        "engineering.fourier_heat_conduction",
        "engineering.thermal_resistance",
        "engineering.stefan_boltzmann",
        "engineering.lmtd",
        "engineering.convective_heat_transfer",
    ]

    def test_all_new_tools_registered(self) -> None:
        registered = {t.full_name for t in REGISTRY.list()}
        missing = [name for name in self._EXPECTED_NEW_TOOLS if name not in registered]
        assert not missing, f"Missing registered tools: {missing}"
