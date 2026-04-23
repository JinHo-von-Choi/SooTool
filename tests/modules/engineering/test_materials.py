"""Tests for engineering.materials tools (Tier 2)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestSafetyFactor:
    def test_safe(self) -> None:
        r = REGISTRY.invoke(
            "engineering.safety_factor",
            allowable_stress="250e6", applied_stress="100e6",
        )
        assert Decimal(r["safety_factor"]) == Decimal("2.5")
        assert r["verdict"] == "safe"

    def test_unsafe(self) -> None:
        r = REGISTRY.invoke(
            "engineering.safety_factor",
            allowable_stress="100e6", applied_stress="150e6",
        )
        assert r["verdict"] == "unsafe"

    def test_absolute_value_for_compression(self) -> None:
        r = REGISTRY.invoke(
            "engineering.safety_factor",
            allowable_stress="200e6", applied_stress="-100e6",
        )
        assert Decimal(r["safety_factor"]) == Decimal("2")

    def test_zero_applied_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.safety_factor",
                allowable_stress="100", applied_stress="0",
            )

    def test_negative_allowable_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.safety_factor",
                allowable_stress="-100", applied_stress="50",
            )


class TestThermalExpansionStrain:
    def test_basic_strain(self) -> None:
        """α=12e-6, ΔT=100 → ε = 1.2e-3."""
        r = REGISTRY.invoke(
            "engineering.thermal_expansion_strain",
            alpha="12e-6", delta_t="100",
        )
        assert Decimal(r["strain"]) == Decimal("0.0012")
        assert "delta_length" not in r

    def test_delta_length(self) -> None:
        """L₀=1 m → ΔL = 1.2e-3 m."""
        r = REGISTRY.invoke(
            "engineering.thermal_expansion_strain",
            alpha="12e-6", delta_t="100", length="1",
        )
        assert Decimal(r["delta_length"]) == Decimal("0.0012")

    def test_negative_dt_gives_negative_strain(self) -> None:
        r = REGISTRY.invoke(
            "engineering.thermal_expansion_strain",
            alpha="12e-6", delta_t="-50",
        )
        assert Decimal(r["strain"]) == Decimal("-0.0006")

    def test_zero_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.thermal_expansion_strain",
                alpha="12e-6", delta_t="100", length="0",
            )


class TestSnFatigueLife:
    def test_basic_cycles(self) -> None:
        """S_a=500, S_f'=1000, b=-0.1 → N_f = 0.5·(0.5)^(-10) = 0.5·1024 = 512."""
        r = REGISTRY.invoke(
            "engineering.sn_fatigue_life",
            stress_amplitude="500",
            fatigue_strength_coeff="1000",
            basquin_exponent="-0.1",
        )
        _assert_close(r["cycles"], Decimal("512"), tol=Decimal("1E-8"))

    def test_stress_equals_coefficient_one_cycle_half(self) -> None:
        """S_a = S_f' → ratio=1 → N_f = 0.5."""
        r = REGISTRY.invoke(
            "engineering.sn_fatigue_life",
            stress_amplitude="800",
            fatigue_strength_coeff="800",
            basquin_exponent="-0.05",
        )
        _assert_close(r["cycles"], Decimal("0.5"), tol=Decimal("1E-15"))

    def test_positive_b_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.sn_fatigue_life",
                stress_amplitude="100",
                fatigue_strength_coeff="1000",
                basquin_exponent="0.1",
            )

    def test_zero_stress_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.sn_fatigue_life",
                stress_amplitude="0",
                fatigue_strength_coeff="1000",
                basquin_exponent="-0.1",
            )

    def test_zero_strength_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.sn_fatigue_life",
                stress_amplitude="100",
                fatigue_strength_coeff="0",
                basquin_exponent="-0.1",
            )


class TestHardnessConvert:
    def test_hv_to_hb(self) -> None:
        """HV → HB: HB = HV / 0.95. HV=200 → HB ≈ 210.526."""
        r = REGISTRY.invoke(
            "engineering.hardness_convert",
            value="200", from_scale="HV", to_scale="HB",
        )
        _assert_close(r["value"], Decimal("210.526315789"), tol=Decimal("1E-6"))
        assert r["scale"] == "HB"

    def test_hb_to_hv(self) -> None:
        r = REGISTRY.invoke(
            "engineering.hardness_convert",
            value="200", from_scale="HB", to_scale="HV",
        )
        assert Decimal(r["value"]) == Decimal("190")

    def test_hv_to_hrc(self) -> None:
        """HRC = 88.887 − 0.058·HV. HV=500 → HRC = 88.887 − 29 = 59.887."""
        r = REGISTRY.invoke(
            "engineering.hardness_convert",
            value="500", from_scale="HV", to_scale="HRC",
        )
        _assert_close(r["value"], Decimal("59.887"), tol=Decimal("1E-9"))

    def test_hrc_to_hv_inverse(self) -> None:
        """HV=400 → HRC → HV roundtrip."""
        hrc = REGISTRY.invoke(
            "engineering.hardness_convert",
            value="400", from_scale="HV", to_scale="HRC",
        )
        back = REGISTRY.invoke(
            "engineering.hardness_convert",
            value=hrc["value"], from_scale="HRC", to_scale="HV",
        )
        _assert_close(back["value"], Decimal("400"), tol=Decimal("1E-6"))

    def test_hrc_out_of_range_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.hardness_convert",
                value="100", from_scale="HRC", to_scale="HV",
            )

    def test_invalid_scale_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.hardness_convert",
                value="100", from_scale="HK", to_scale="HV",
            )


class TestConcurrency:
    def test_safety_factor_batch_race_free(self) -> None:
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.safety_factor",
                allowable_stress=str(n * 10),
                applied_stress="10",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            assert Decimal(res["safety_factor"]) == Decimal(n), f"mismatch at n={n}"
