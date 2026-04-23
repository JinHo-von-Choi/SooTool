"""Tests for engineering.mechanical tools."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestMechStress:
    def test_basic(self) -> None:
        r = REGISTRY.invoke("engineering.mech_stress", force="1000", area="0.01")
        assert Decimal(r["stress"]) == Decimal("100000")
        assert "trace" in r

    def test_compression_negative_force(self) -> None:
        """Negative force (compression) permitted; returns negative stress."""
        r = REGISTRY.invoke("engineering.mech_stress", force="-500", area="0.01")
        assert Decimal(r["stress"]) == Decimal("-50000")

    def test_zero_area_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("engineering.mech_stress", force="1000", area="0")

    def test_trace_structure(self) -> None:
        r = REGISTRY.invoke("engineering.mech_stress", force="100", area="1")
        assert r["trace"]["tool"] == "engineering.mech_stress"
        assert "inputs" in r["trace"]


class TestMechStrain:
    def test_basic(self) -> None:
        """ΔL=0.001 m, L=1 m → ε = 0.001."""
        r = REGISTRY.invoke(
            "engineering.mech_strain", delta_length="0.001", original_length="1",
        )
        _assert_close(r["strain"], Decimal("0.001"))

    def test_negative_delta(self) -> None:
        """Compressive strain permitted."""
        r = REGISTRY.invoke(
            "engineering.mech_strain", delta_length="-0.002", original_length="2",
        )
        _assert_close(r["strain"], Decimal("-0.001"))

    def test_zero_original_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.mech_strain", delta_length="0.001", original_length="0",
            )

    def test_zero_delta_gives_zero_strain(self) -> None:
        r = REGISTRY.invoke(
            "engineering.mech_strain", delta_length="0", original_length="1",
        )
        assert Decimal(r["strain"]) == Decimal("0")


class TestElasticModulusRelate:
    def test_young_poisson(self) -> None:
        """E=200e9, ν=0.3 → G = E/(2(1+ν)) = 200e9/2.6 ≈ 76.923e9."""
        r = REGISTRY.invoke(
            "engineering.elastic_modulus_relate",
            young="200e9", poisson="0.3",
        )
        _assert_close(Decimal(r["shear"]) / Decimal("1e9"), Decimal("76.923076923"), tol=Decimal("1E-6"))
        # K = E / (3(1-2ν)) = 200e9 / (3 × 0.4) = 166.666e9
        _assert_close(Decimal(r["bulk"]) / Decimal("1e9"), Decimal("166.66666666"), tol=Decimal("1E-6"))

    def test_young_shear(self) -> None:
        """E=200e9, G=76.923e9 → ν = E/(2G) - 1 ≈ 0.3."""
        r = REGISTRY.invoke(
            "engineering.elastic_modulus_relate",
            young="200e9", shear="76923076923.07692",
        )
        _assert_close(r["poisson"], Decimal("0.3"), tol=Decimal("1E-6"))

    def test_shear_bulk(self) -> None:
        """G=80e9, K=160e9 → ν = (3K-2G)/(2(3K+G)) = (480-160)/(2·560) = 320/1120 ≈ 0.2857."""
        r = REGISTRY.invoke(
            "engineering.elastic_modulus_relate",
            shear="80e9", bulk="160e9",
        )
        _assert_close(r["poisson"], Decimal("0.2857142857"), tol=Decimal("1E-6"))

    def test_poisson_bulk(self) -> None:
        """K=100e9, ν=0.25 → E = 3K(1-2ν) = 3·100e9·0.5 = 150e9."""
        r = REGISTRY.invoke(
            "engineering.elastic_modulus_relate",
            bulk="100e9", poisson="0.25",
        )
        _assert_close(Decimal(r["young"]) / Decimal("1e9"), Decimal("150"), tol=Decimal("1E-6"))

    def test_overdetermined_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.elastic_modulus_relate",
                young="200e9", shear="76e9", poisson="0.3",
            )

    def test_underdetermined_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.elastic_modulus_relate", young="200e9",
            )

    def test_invalid_poisson_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.elastic_modulus_relate",
                young="200e9", poisson="0.5",
            )


class TestTorqueRotationalPower:
    def test_basic(self) -> None:
        """τ=100, ω=10 → P=1000 W."""
        r = REGISTRY.invoke(
            "engineering.torque_rotational_power",
            torque="100", angular_velocity="10",
        )
        assert Decimal(r["power"]) == Decimal("1000")

    def test_zero_torque(self) -> None:
        r = REGISTRY.invoke(
            "engineering.torque_rotational_power",
            torque="0", angular_velocity="100",
        )
        assert Decimal(r["power"]) == Decimal("0")

    def test_negative_sign_preserved(self) -> None:
        r = REGISTRY.invoke(
            "engineering.torque_rotational_power",
            torque="-50", angular_velocity="10",
        )
        assert Decimal(r["power"]) == Decimal("-500")

    def test_trace_has_formula(self) -> None:
        r = REGISTRY.invoke(
            "engineering.torque_rotational_power",
            torque="10", angular_velocity="10",
        )
        assert r["trace"]["formula"] == "P = τ × ω"


class TestMomentOfInertia:
    def test_solid_disk(self) -> None:
        """I = ½ m r² ; m=10, r=2 → I=20."""
        r = REGISTRY.invoke(
            "engineering.moment_of_inertia",
            shape="solid_disk", mass="10", radius="2",
        )
        assert Decimal(r["moment_of_inertia"]) == Decimal("20")

    def test_thin_ring(self) -> None:
        """I = m r² ; m=5, r=3 → I=45."""
        r = REGISTRY.invoke(
            "engineering.moment_of_inertia",
            shape="thin_ring", mass="5", radius="3",
        )
        assert Decimal(r["moment_of_inertia"]) == Decimal("45")

    def test_thin_rod_center(self) -> None:
        """I = (1/12) m L² ; m=12, L=1 → I=1."""
        r = REGISTRY.invoke(
            "engineering.moment_of_inertia",
            shape="thin_rod_center", mass="12", length="1",
        )
        assert Decimal(r["moment_of_inertia"]) == Decimal("1")

    def test_thin_rod_end(self) -> None:
        """I = (1/3) m L² ; m=3, L=1 → I≈1 (Decimal 1/3 rounding)."""
        r = REGISTRY.invoke(
            "engineering.moment_of_inertia",
            shape="thin_rod_end", mass="3", length="1",
        )
        _assert_close(r["moment_of_inertia"], Decimal("1"), tol=Decimal("1E-40"))

    def test_solid_sphere(self) -> None:
        """I = (2/5) m r² ; m=5, r=2 → 2/5·5·4 = 8."""
        r = REGISTRY.invoke(
            "engineering.moment_of_inertia",
            shape="solid_sphere", mass="5", radius="2",
        )
        assert Decimal(r["moment_of_inertia"]) == Decimal("8")

    def test_invalid_shape_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.moment_of_inertia",
                shape="torus", mass="1", radius="1",
            )

    def test_missing_radius_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.moment_of_inertia",
                shape="solid_disk", mass="1",
            )

    def test_missing_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.moment_of_inertia",
                shape="thin_rod_center", mass="1",
            )

    def test_zero_mass_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.moment_of_inertia",
                shape="solid_disk", mass="0", radius="1",
            )


class TestConcurrency:
    def test_mech_stress_batch_race_free(self) -> None:
        """engineering.mech_stress must be thread-safe under N=100 concurrent calls."""
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.mech_stress",
                force=str(n),
                area="1",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            assert Decimal(res["stress"]) == Decimal(n), f"mismatch at n={n}"
