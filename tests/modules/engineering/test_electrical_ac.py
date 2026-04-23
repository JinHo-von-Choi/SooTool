"""Tests for engineering.electrical_ac tools."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401 — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestAcImpedance:
    def test_series_r_only(self) -> None:
        """Pure resistor at any f: |Z|=R, phase=0."""
        result = REGISTRY.invoke(
            "engineering.ac_impedance",
            frequency="60", resistance="50", inductance="0", capacitance="0",
        )
        assert Decimal(result["magnitude"]) == Decimal("50")
        assert abs(Decimal(result["phase_deg"])) < Decimal("1E-6")
        assert "trace" in result

    def test_series_rl(self) -> None:
        """R=3, XL=4 → |Z|=5, phase=atan(4/3)≈53.13°."""
        # Choose L so that ωL = 4 at f = 1/(2π). Simpler: pick ω such that L=4/ω.
        # Use f=1/(2π), inductance=4 → ωL = 4.
        import math
        f = "0.15915494309189535"
        result = REGISTRY.invoke(
            "engineering.ac_impedance",
            frequency=f, resistance="3", inductance="4", capacitance="0",
        )
        _assert_close(result["magnitude"], Decimal("5"), tol=Decimal("1E-6"))
        _assert_close(result["phase_deg"], Decimal(str(math.degrees(math.atan2(4, 3)))), tol=Decimal("1E-5"))

    def test_parallel_topology_valid(self) -> None:
        """Parallel R only returns resistance unchanged at any freq."""
        result = REGISTRY.invoke(
            "engineering.ac_impedance",
            frequency="60", resistance="100", inductance="0", capacitance="0",
            topology="parallel",
        )
        _assert_close(result["magnitude"], Decimal("100"))

    def test_invalid_topology_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.ac_impedance",
                frequency="60", resistance="10", topology="weird",
            )

    def test_negative_resistance_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.ac_impedance",
                frequency="60", resistance="-1",
            )

    def test_zero_frequency_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.ac_impedance",
                frequency="0", resistance="10",
            )


class TestRlcTimeConstant:
    def test_rc(self) -> None:
        """τ = RC = 1000 × 1e-6 = 1e-3 s."""
        r = REGISTRY.invoke(
            "engineering.rlc_time_constant",
            mode="rc", resistance="1000", capacitance="0.000001",
        )
        _assert_close(r["tau"], Decimal("0.001"))
        assert "trace" in r

    def test_rl(self) -> None:
        """τ = L/R = 2/10 = 0.2 s."""
        r = REGISTRY.invoke(
            "engineering.rlc_time_constant",
            mode="rl", resistance="10", inductance="2",
        )
        _assert_close(r["tau"], Decimal("0.2"))

    def test_rlc_underdamped(self) -> None:
        r = REGISTRY.invoke(
            "engineering.rlc_time_constant",
            mode="rlc", resistance="1", inductance="1", capacitance="1",
        )
        assert r["regime"] == "underdamped"
        _assert_close(r["alpha"], Decimal("0.5"))
        _assert_close(r["omega0"], Decimal("1"))

    def test_rlc_overdamped(self) -> None:
        r = REGISTRY.invoke(
            "engineering.rlc_time_constant",
            mode="rlc", resistance="10", inductance="1", capacitance="1",
        )
        assert r["regime"] == "overdamped"

    def test_rlc_critical(self) -> None:
        # α = ω0 → R/(2L) = 1/√(LC); choose L=1, C=1, R=2
        r = REGISTRY.invoke(
            "engineering.rlc_time_constant",
            mode="rlc", resistance="2", inductance="1", capacitance="1",
        )
        assert r["regime"] == "critically_damped"

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.rlc_time_constant", mode="xyz", resistance="10",
            )

    def test_rc_missing_capacitance_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.rlc_time_constant", mode="rc", resistance="10",
            )


class TestLcResonantFrequency:
    def test_basic(self) -> None:
        """L=1, C=1 → f = 1/(2π) ≈ 0.15915..."""
        r = REGISTRY.invoke(
            "engineering.lc_resonant_frequency", inductance="1", capacitance="1",
        )
        _assert_close(r["frequency"], Decimal("0.15915494309189535"), tol=Decimal("1E-10"))

    def test_tank_circuit(self) -> None:
        """L=10mH, C=100nF → f ≈ 5032.92 Hz."""
        r = REGISTRY.invoke(
            "engineering.lc_resonant_frequency",
            inductance="0.01", capacitance="0.0000001",
        )
        _assert_close(r["frequency"], Decimal("5032.921"), tol=Decimal("0.001"))

    def test_zero_inductance_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.lc_resonant_frequency",
                inductance="0", capacitance="1",
            )

    def test_negative_capacitance_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.lc_resonant_frequency",
                inductance="1", capacitance="-1",
            )


class TestRcFilterCutoff:
    def test_low_pass(self) -> None:
        """R=1k, C=1μF → fc = 1/(2π·1e-3) ≈ 159.155 Hz."""
        r = REGISTRY.invoke(
            "engineering.rc_filter_cutoff",
            resistance="1000", capacitance="0.000001",
            filter_type="low_pass",
        )
        _assert_close(r["cutoff_hz"], Decimal("159.1549430918954"), tol=Decimal("1E-6"))
        assert r["filter_type"] == "low_pass"

    def test_high_pass(self) -> None:
        """Same formula, high_pass label."""
        r = REGISTRY.invoke(
            "engineering.rc_filter_cutoff",
            resistance="1000", capacitance="0.000001",
            filter_type="high_pass",
        )
        _assert_close(r["cutoff_hz"], Decimal("159.1549430918954"), tol=Decimal("1E-6"))
        assert r["filter_type"] == "high_pass"

    def test_invalid_filter_type_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.rc_filter_cutoff",
                resistance="1000", capacitance="1e-6", filter_type="band_pass",
            )

    def test_zero_resistance_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.rc_filter_cutoff",
                resistance="0", capacitance="1e-6",
            )


class TestCapacitorCombine:
    def test_parallel_sum(self) -> None:
        r = REGISTRY.invoke(
            "engineering.capacitor_combine",
            capacitors=["1", "2", "3"], topology="parallel",
        )
        assert Decimal(r["total"]) == Decimal("6")

    def test_series_reciprocal(self) -> None:
        """1/C = 1/1 + 1/1 + 1/1 → C = 1/3."""
        r = REGISTRY.invoke(
            "engineering.capacitor_combine",
            capacitors=["1", "1", "1"], topology="series",
        )
        _assert_close(r["total"], Decimal("0.3333333333333333"), tol=Decimal("1E-6"))

    def test_single_capacitor(self) -> None:
        r = REGISTRY.invoke(
            "engineering.capacitor_combine",
            capacitors=["5"], topology="parallel",
        )
        assert Decimal(r["total"]) == Decimal("5")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.capacitor_combine", capacitors=[], topology="parallel",
            )

    def test_negative_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.capacitor_combine",
                capacitors=["1", "-2"], topology="parallel",
            )


class TestInductorCombine:
    def test_series_sum(self) -> None:
        r = REGISTRY.invoke(
            "engineering.inductor_combine",
            inductors=["2", "3", "5"], topology="series",
        )
        assert Decimal(r["total"]) == Decimal("10")

    def test_parallel_reciprocal(self) -> None:
        """1/L = 1/2 + 1/2 → L = 1."""
        r = REGISTRY.invoke(
            "engineering.inductor_combine",
            inductors=["2", "2"], topology="parallel",
        )
        _assert_close(r["total"], Decimal("1"))

    def test_invalid_topology_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.inductor_combine",
                inductors=["1"], topology="weird",
            )

    def test_zero_value_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.inductor_combine",
                inductors=["1", "0"], topology="series",
            )


class TestThreePhasePower:
    def test_balanced_load(self) -> None:
        """V=400V line, I=10A line, PF=0.866 → S=√3·4000≈6928.2032, P=S·PF≈5999.824."""
        r = REGISTRY.invoke(
            "engineering.three_phase_power",
            line_voltage="400", line_current="10", power_factor="0.866",
        )
        _assert_close(r["apparent"], Decimal("6928.203230275509"), tol=Decimal("1E-4"))
        _assert_close(r["real"],     Decimal("5999.823997418"),   tol=Decimal("1E-6"))
        assert Decimal(r["reactive"]) > Decimal("0")

    def test_unity_power_factor(self) -> None:
        r = REGISTRY.invoke(
            "engineering.three_phase_power",
            line_voltage="100", line_current="10", power_factor="1",
        )
        _assert_close(r["real"], Decimal(r["apparent"]))
        _assert_close(r["reactive"], Decimal("0"), tol=Decimal("1E-6"))

    def test_delta_topology_accepted(self) -> None:
        r = REGISTRY.invoke(
            "engineering.three_phase_power",
            line_voltage="400", line_current="10", power_factor="1",
            connection="delta",
        )
        assert Decimal(r["real"]) > Decimal("0")

    def test_pf_out_of_range_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.three_phase_power",
                line_voltage="400", line_current="10", power_factor="1.5",
            )

    def test_bad_connection_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.three_phase_power",
                line_voltage="400", line_current="10", power_factor="1",
                connection="star",
            )


class TestPowerFactorCorrection:
    def test_basic(self) -> None:
        r = REGISTRY.invoke(
            "engineering.power_factor_correction",
            real_power="10000", current_pf="0.7", target_pf="0.95",
            voltage="400", frequency="60",
        )
        # Expect a positive capacitance and positive Q_c
        assert Decimal(r["capacitance"]) > Decimal("0")
        assert Decimal(r["reactive_power_canceled"]) > Decimal("0")

    def test_target_not_greater_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.power_factor_correction",
                real_power="1000", current_pf="0.9", target_pf="0.9",
                voltage="400", frequency="60",
            )

    def test_pf_out_of_range_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.power_factor_correction",
                real_power="1000", current_pf="1.5", target_pf="0.95",
                voltage="400", frequency="60",
            )

    def test_zero_power_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.power_factor_correction",
                real_power="0", current_pf="0.7", target_pf="0.9",
                voltage="400", frequency="60",
            )


class TestDbConvert:
    def test_p_to_db(self) -> None:
        """10 log10(100/1) = 20 dB."""
        r = REGISTRY.invoke(
            "engineering.db_convert", mode="p_to_db", value="100", reference="1",
        )
        _assert_close(r["result"], Decimal("20"), tol=Decimal("1E-6"))

    def test_v_to_db(self) -> None:
        """20 log10(10) = 20 dB."""
        r = REGISTRY.invoke(
            "engineering.db_convert", mode="v_to_db", value="10", reference="1",
        )
        _assert_close(r["result"], Decimal("20"), tol=Decimal("1E-6"))

    def test_db_to_p_roundtrip(self) -> None:
        """10^(20/10) = 100."""
        r = REGISTRY.invoke(
            "engineering.db_convert", mode="db_to_p", value="20",
        )
        _assert_close(r["result"], Decimal("100"), tol=Decimal("1E-6"))

    def test_w_to_dbm_and_back(self) -> None:
        """1 mW = 0 dBm; 1 W = 30 dBm."""
        r1 = REGISTRY.invoke(
            "engineering.db_convert", mode="w_to_dbm", value="0.001",
        )
        _assert_close(r1["result"], Decimal("0"), tol=Decimal("1E-6"))
        r2 = REGISTRY.invoke(
            "engineering.db_convert", mode="w_to_dbm", value="1",
        )
        _assert_close(r2["result"], Decimal("30"), tol=Decimal("1E-6"))
        r3 = REGISTRY.invoke(
            "engineering.db_convert", mode="dbm_to_w", value="30",
        )
        _assert_close(r3["result"], Decimal("1"), tol=Decimal("1E-6"))

    def test_np_db_conversion(self) -> None:
        """1 Np = 20/ln(10) ≈ 8.685889638 dB."""
        r = REGISTRY.invoke(
            "engineering.db_convert", mode="np_to_db", value="1",
        )
        _assert_close(r["result"], Decimal("8.685889638065035"), tol=Decimal("1E-6"))

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.db_convert", mode="bogus", value="1",
            )

    def test_v_to_db_negative_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.db_convert", mode="v_to_db", value="-1",
            )


class TestResistorColorCode:
    def test_4band_brown_black_red_gold(self) -> None:
        """10 × 100 = 1000Ω, ±5%."""
        r = REGISTRY.invoke(
            "engineering.resistor_color_code",
            bands=["brown", "black", "red", "gold"],
        )
        assert Decimal(r["resistance_ohm"]) == Decimal("1000")
        assert Decimal(r["tolerance_pct"])  == Decimal("5")

    def test_4band_yellow_violet_orange_silver(self) -> None:
        """47 × 1000 = 47kΩ, ±10%."""
        r = REGISTRY.invoke(
            "engineering.resistor_color_code",
            bands=["yellow", "violet", "orange", "silver"],
        )
        assert Decimal(r["resistance_ohm"]) == Decimal("47000")
        assert Decimal(r["tolerance_pct"])  == Decimal("10")

    def test_5band_precision(self) -> None:
        """123 × 10 = 1230 Ω, ±1%."""
        r = REGISTRY.invoke(
            "engineering.resistor_color_code",
            bands=["brown", "red", "orange", "brown", "brown"],
        )
        assert Decimal(r["resistance_ohm"]) == Decimal("1230")
        assert Decimal(r["tolerance_pct"])  == Decimal("1")

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.resistor_color_code",
                bands=["brown", "black", "red"],
            )

    def test_invalid_digit_color_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.resistor_color_code",
                bands=["gold", "black", "red", "gold"],   # gold invalid as digit
            )

    def test_invalid_tolerance_color_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.resistor_color_code",
                bands=["brown", "black", "red", "black"],  # black invalid tolerance
            )


class TestOpampGain:
    def test_inverting(self) -> None:
        """Rf=10k, Rin=1k, inverting → -10."""
        r = REGISTRY.invoke(
            "engineering.opamp_gain",
            feedback_resistance="10000", input_resistance="1000",
            configuration="inverting",
        )
        assert Decimal(r["gain"]) == Decimal("-10")

    def test_non_inverting(self) -> None:
        """Rf=10k, Rin=1k, non-inverting → 1+10 = 11."""
        r = REGISTRY.invoke(
            "engineering.opamp_gain",
            feedback_resistance="10000", input_resistance="1000",
            configuration="non_inverting",
        )
        assert Decimal(r["gain"]) == Decimal("11")

    def test_invalid_config_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.opamp_gain",
                feedback_resistance="1000", input_resistance="1000",
                configuration="differential",
            )

    def test_zero_rin_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.opamp_gain",
                feedback_resistance="1000", input_resistance="0",
            )


class TestConcurrency:
    def test_ac_impedance_batch_race_free(self) -> None:
        """engineering.ac_impedance must be thread-safe under N=100 concurrent calls."""
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.ac_impedance",
                frequency="60",
                resistance=str(n),
                inductance="0",
                capacitance="0",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            assert Decimal(res["magnitude"]) == Decimal(n), f"mismatch at n={n}"
