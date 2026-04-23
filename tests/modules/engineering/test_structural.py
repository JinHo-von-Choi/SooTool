"""Tests for engineering.structural tools (Tier 2)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestBeamDeflection:
    def test_cantilever_point_end(self) -> None:
        """δ = P L³ / (3 E I); P=1000, L=2, E=200e9, I=1e-6 → 4/600000 ≈ 6.6667e-6."""
        r = REGISTRY.invoke(
            "engineering.beam_deflection",
            case="cantilever_point_end",
            length="2", young="200e9", inertia="1e-6", load="1000",
        )
        expected = Decimal("1000") * Decimal("8") / (Decimal("3") * Decimal("200e9") * Decimal("1e-6"))
        _assert_close(r["deflection"], expected, tol=Decimal("1E-12"))

    def test_simply_supported_uniform(self) -> None:
        """δ = 5 w L⁴ / (384 E I)."""
        r = REGISTRY.invoke(
            "engineering.beam_deflection",
            case="simply_supported_uniform",
            length="3", young="210e9", inertia="5e-7", load="2000",
        )
        expected = Decimal("5") * Decimal("2000") * Decimal("81") / (
            Decimal("384") * Decimal("210e9") * Decimal("5e-7")
        )
        _assert_close(r["deflection"], expected, tol=Decimal("1E-12"))

    def test_cantilever_uniform(self) -> None:
        r = REGISTRY.invoke(
            "engineering.beam_deflection",
            case="cantilever_uniform",
            length="1", young="200e9", inertia="1e-6", load="500",
        )
        expected = Decimal("500") / (Decimal("8") * Decimal("200e9") * Decimal("1e-6"))
        _assert_close(r["deflection"], expected, tol=Decimal("1E-12"))

    def test_simply_supported_point_center(self) -> None:
        r = REGISTRY.invoke(
            "engineering.beam_deflection",
            case="simply_supported_point_center",
            length="2", young="200e9", inertia="1e-6", load="1000",
        )
        expected = Decimal("1000") * Decimal("8") / (Decimal("48") * Decimal("200e9") * Decimal("1e-6"))
        _assert_close(r["deflection"], expected, tol=Decimal("1E-12"))

    def test_invalid_case_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.beam_deflection",
                case="fixed_fixed_middle",
                length="1", young="1", inertia="1", load="1",
            )

    def test_zero_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.beam_deflection",
                case="cantilever_point_end",
                length="0", young="1", inertia="1", load="1",
            )

    def test_negative_load_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.beam_deflection",
                case="cantilever_point_end",
                length="1", young="1", inertia="1", load="-10",
            )


class TestBendingStress:
    def test_basic(self) -> None:
        """M=1000, c=0.05, I=1e-6 → σ = 5e7."""
        r = REGISTRY.invoke(
            "engineering.bending_stress",
            moment="1000", distance_neutral="0.05", inertia="1e-6",
        )
        assert Decimal(r["stress"]) == Decimal("5e7")

    def test_negative_moment(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bending_stress",
            moment="-200", distance_neutral="0.01", inertia="1e-6",
        )
        assert Decimal(r["stress"]) == Decimal("-2e6")

    def test_zero_inertia_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bending_stress",
                moment="100", distance_neutral="0.01", inertia="0",
            )

    def test_trace_formula(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bending_stress",
            moment="1", distance_neutral="1", inertia="1",
        )
        assert r["trace"]["formula"] == "σ = M c / I"


class TestShearStress:
    def test_average(self) -> None:
        r = REGISTRY.invoke(
            "engineering.shear_stress",
            mode="average", shear_force="1000", area="0.01",
        )
        assert Decimal(r["shear_stress"]) == Decimal("100000")

    def test_rectangular_max(self) -> None:
        r = REGISTRY.invoke(
            "engineering.shear_stress",
            mode="rectangular_max", shear_force="1000", area="0.01",
        )
        assert Decimal(r["shear_stress"]) == Decimal("150000")

    def test_general(self) -> None:
        """τ = V Q / (I b); V=500, Q=1e-5, I=1e-6, b=0.1 → τ=50000."""
        r = REGISTRY.invoke(
            "engineering.shear_stress",
            mode="general", shear_force="500",
            first_moment_q="1e-5", inertia="1e-6", width="0.1",
        )
        assert Decimal(r["shear_stress"]) == Decimal("50000")

    def test_general_missing_params_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.shear_stress",
                mode="general", shear_force="100",
            )

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.shear_stress",
                mode="elliptical", shear_force="1", area="1",
            )


class TestEulerBuckling:
    def test_pinned_pinned(self) -> None:
        """K=1, E=200e9, I=1e-6, L=2 → P_cr = π²·200e9·1e-6 / 4 ≈ 4.9348e4."""
        r = REGISTRY.invoke(
            "engineering.euler_buckling",
            young="200e9", inertia="1e-6", length="2",
            end_condition="pinned_pinned",
        )
        # Approximate expected (π²·E·I/L²); tol loose because of π precision
        import math
        expected = math.pi ** 2 * 200e9 * 1e-6 / 4
        _assert_close(r["critical_load"], Decimal(str(expected)), tol=Decimal("1E-4"))

    def test_fixed_free(self) -> None:
        r = REGISTRY.invoke(
            "engineering.euler_buckling",
            young="1e9", inertia="1e-6", length="1",
            end_condition="fixed_free",
        )
        # K=2 → (K L)² = 4
        import math
        expected = math.pi ** 2 * 1e9 * 1e-6 / 4
        _assert_close(r["critical_load"], Decimal(str(expected)), tol=Decimal("1E-4"))

    def test_custom_k(self) -> None:
        r = REGISTRY.invoke(
            "engineering.euler_buckling",
            young="1e9", inertia="1e-6", length="1",
            effective_length_factor="0.7",
        )
        import math
        expected = math.pi ** 2 * 1e9 * 1e-6 / (0.7 ** 2)
        _assert_close(r["critical_load"], Decimal(str(expected)), tol=Decimal("1E-4"))

    def test_both_end_condition_and_k_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.euler_buckling",
                young="1", inertia="1", length="1",
                end_condition="pinned_pinned",
                effective_length_factor="0.5",
            )

    def test_neither_end_condition_nor_k_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.euler_buckling",
                young="1", inertia="1", length="1",
            )

    def test_invalid_end_condition_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.euler_buckling",
                young="1", inertia="1", length="1",
                end_condition="invalid",
            )


class TestSectionMomentInertia:
    def test_rectangle(self) -> None:
        """b=0.1, h=0.2 → I = 0.1·0.008/12 = 6.6667e-5."""
        r = REGISTRY.invoke(
            "engineering.section_moment_inertia",
            shape="rectangle", width="0.1", height="0.2",
        )
        expected = Decimal("0.1") * Decimal("0.008") / Decimal("12")
        _assert_close(r["inertia"], expected, tol=Decimal("1E-12"))

    def test_circle(self) -> None:
        """d=0.1 → I = π·1e-4/64 ≈ 4.9087e-6."""
        r = REGISTRY.invoke(
            "engineering.section_moment_inertia",
            shape="circle", diameter="0.1",
        )
        import math
        expected = math.pi * (0.1 ** 4) / 64
        _assert_close(r["inertia"], Decimal(str(expected)), tol=Decimal("1E-10"))

    def test_i_beam(self) -> None:
        """간단 I형: flange 0.1×0.01, web 0.2×0.005 → H=0.22.
        I = 0.1·0.22³/12 − 0.095·0.2³/12
          = 0.1·0.010648/12 − 0.095·0.008/12
        """
        r = REGISTRY.invoke(
            "engineering.section_moment_inertia",
            shape="i_beam",
            flange_width="0.1", flange_thickness="0.01",
            web_height="0.2",  web_thickness="0.005",
        )
        total_h = Decimal("0.22")
        outer = Decimal("0.1") * total_h ** 3 / Decimal("12")
        inner = (Decimal("0.1") - Decimal("0.005")) * Decimal("0.2") ** 3 / Decimal("12")
        expected = outer - inner
        _assert_close(r["inertia"], expected, tol=Decimal("1E-12"))

    def test_rectangle_missing_height_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.section_moment_inertia",
                shape="rectangle", width="0.1",
            )

    def test_circle_zero_diameter_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.section_moment_inertia",
                shape="circle", diameter="0",
            )

    def test_invalid_shape_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.section_moment_inertia",
                shape="triangle", width="1", height="1",
            )


class TestConcurrency:
    def test_bending_stress_batch_race_free(self) -> None:
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.bending_stress",
                moment=str(n), distance_neutral="1", inertia="1",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            assert Decimal(res["stress"]) == Decimal(n), f"mismatch at n={n}"
