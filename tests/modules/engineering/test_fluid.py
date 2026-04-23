"""Tests for engineering.fluid tools (Reynolds number + new Phase-4 extensions)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestFluidReynolds:
    def test_reynolds_water_pipe(self) -> None:
        """ρ=1000, v=1, L=0.01, μ=0.001 → Re=10000 (turbulent)."""
        result = REGISTRY.invoke(
            "engineering.fluid_reynolds",
            density="1000",
            velocity="1",
            length="0.01",
            viscosity="0.001",
        )
        assert Decimal(result["reynolds"]) == Decimal("10000")
        assert result["regime"] == "turbulent"
        assert "trace" in result

    def test_reynolds_laminar(self) -> None:
        """Re < 2300 → laminar. ρ=1000, v=0.001, L=0.01, μ=0.001 → Re=10."""
        result = REGISTRY.invoke(
            "engineering.fluid_reynolds",
            density="1000",
            velocity="0.001",
            length="0.01",
            viscosity="0.001",
        )
        assert Decimal(result["reynolds"]) == Decimal("10")
        assert result["regime"] == "laminar"

    def test_reynolds_transitional(self) -> None:
        """Re in [2300, 4000] → transitional. Target Re=3000."""
        # Re = ρvL/μ = 1000*0.3*0.01/0.001 = 3000
        result = REGISTRY.invoke(
            "engineering.fluid_reynolds",
            density="1000",
            velocity="0.3",
            length="0.01",
            viscosity="0.001",
        )
        re = Decimal(result["reynolds"])
        assert re == Decimal("3000")
        assert result["regime"] == "transitional"

    def test_reynolds_boundary_laminar_edge(self) -> None:
        """Re exactly at 2300 → transitional (not laminar, since 2300 is not < 2300)."""
        # Re = 1000 * v * 0.01 / 0.001 = 10000v; want 2300 → v = 0.23
        result = REGISTRY.invoke(
            "engineering.fluid_reynolds",
            density="1000",
            velocity="0.23",
            length="0.01",
            viscosity="0.001",
        )
        assert result["regime"] == "transitional"

    def test_reynolds_boundary_turbulent_edge(self) -> None:
        """Re exactly at 4000 → transitional (not turbulent, since 4000 is not > 4000)."""
        # Re = 1000 * v * 0.01 / 0.001; want 4000 → v = 0.4
        result = REGISTRY.invoke(
            "engineering.fluid_reynolds",
            density="1000",
            velocity="0.4",
            length="0.01",
            viscosity="0.001",
        )
        assert result["regime"] == "transitional"

    def test_reynolds_zero_density_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.fluid_reynolds",
                density="0",
                velocity="1",
                length="0.01",
                viscosity="0.001",
            )

    def test_reynolds_zero_velocity_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.fluid_reynolds",
                density="1000",
                velocity="0",
                length="0.01",
                viscosity="0.001",
            )

    def test_reynolds_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "engineering.fluid_reynolds",
            density="1000",
            velocity="1",
            length="0.01",
            viscosity="0.001",
        )
        trace = result["trace"]
        assert trace["tool"] == "engineering.fluid_reynolds"
        assert "inputs" in trace


class TestBernoulli:
    def test_solve_pressure_2(self) -> None:
        """Stationary elevation drop 10 m with water: P₂ = P₁ + ρgz₁.
        P₁=100000, v₁=0, z₁=10, v₂=0, z₂=0, ρ=1000, g=9.80665 → P₂ = 100000 + 98066.5 = 198066.5.
        """
        r = REGISTRY.invoke(
            "engineering.bernoulli",
            pressure_1="100000", velocity_1="0", elevation_1="10",
            density="1000",
            velocity_2="0", elevation_2="0",
        )
        _assert_close(r["pressure_2"], Decimal("198066.5"), tol=Decimal("1E-6"))

    def test_solve_velocity_2(self) -> None:
        """Torricelli: v₂=√(2·g·z) with g=9.80665 → √196.133 ≈ 14.00474919."""
        r = REGISTRY.invoke(
            "engineering.bernoulli",
            pressure_1="0", velocity_1="0", elevation_1="10",
            density="1000",
            pressure_2="0", elevation_2="0",
        )
        _assert_close(r["velocity_2"], Decimal("14.004749194469710"), tol=Decimal("1E-6"))

    def test_solve_elevation_2(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bernoulli",
            pressure_1="100000", velocity_1="0", elevation_1="0",
            density="1000",
            pressure_2="100000", velocity_2="0",
        )
        _assert_close(r["elevation_2"], Decimal("0"), tol=Decimal("1E-6"))

    def test_multiple_unknowns_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bernoulli",
                pressure_1="0", velocity_1="0", elevation_1="0",
                density="1000",
            )

    def test_impossible_velocity_raises(self) -> None:
        """If pressure rises without enough reservoir energy, v²<0."""
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bernoulli",
                pressure_1="0", velocity_1="0", elevation_1="0",
                density="1000",
                pressure_2="100000", elevation_2="0",
            )

    def test_zero_density_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bernoulli",
                pressure_1="0", velocity_1="0", elevation_1="0",
                density="0",
                velocity_2="0", elevation_2="0",
            )


class TestDarcyWeisbach:
    def test_basic(self) -> None:
        """f=0.02, L=100, D=0.1, v=2, g=9.80665 → h_f = 0.02·1000·4/(2·9.80665) ≈ 4.0789."""
        r = REGISTRY.invoke(
            "engineering.darcy_weisbach",
            friction_factor="0.02", length="100", diameter="0.1", velocity="2",
        )
        _assert_close(r["head_loss_m"], Decimal("4.078864851911713"), tol=Decimal("1E-6"))

    def test_pressure_drop_includes_density(self) -> None:
        r = REGISTRY.invoke(
            "engineering.darcy_weisbach",
            friction_factor="0.02", length="100", diameter="0.1", velocity="2",
            density="1000",
        )
        # ΔP = ρ g h_f ≈ 1000 × 9.80665 × 4.078 ≈ 40000
        assert Decimal(r["pressure_drop_pa"]) > Decimal("39000")
        assert Decimal(r["pressure_drop_pa"]) < Decimal("41000")

    def test_zero_velocity_gives_zero_loss(self) -> None:
        r = REGISTRY.invoke(
            "engineering.darcy_weisbach",
            friction_factor="0.02", length="100", diameter="0.1", velocity="0",
        )
        assert Decimal(r["head_loss_m"]) == Decimal("0")

    def test_invalid_friction_factor_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.darcy_weisbach",
                friction_factor="0", length="100", diameter="0.1", velocity="2",
            )

    def test_negative_velocity_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.darcy_weisbach",
                friction_factor="0.02", length="100", diameter="0.1", velocity="-1",
            )


class TestMoodyFrictionFactor:
    def test_laminar(self) -> None:
        """Re=1000 < 2300 → f = 64/Re = 0.064, iterations=0."""
        r = REGISTRY.invoke(
            "engineering.moody_friction_factor",
            reynolds="1000", roughness="0", diameter="0.1",
        )
        _assert_close(r["friction_factor"], Decimal("0.064"), tol=Decimal("1E-8"))
        assert r["regime"] == "laminar"
        assert r["iterations"] == 0

    def test_turbulent_smooth_pipe(self) -> None:
        """Re=100000, smooth pipe → Colebrook converges; Swamee-Jain ≈ 0.01797."""
        r = REGISTRY.invoke(
            "engineering.moody_friction_factor",
            reynolds="100000", roughness="0", diameter="0.1",
        )
        assert r["regime"] == "turbulent"
        assert r["iterations"] >= 1
        # Reference (Colebrook smooth pipe, Re=1e5): f ≈ 0.01798
        assert Decimal(r["friction_factor"]) > Decimal("0.017")
        assert Decimal(r["friction_factor"]) < Decimal("0.019")

    def test_turbulent_rough_pipe(self) -> None:
        r = REGISTRY.invoke(
            "engineering.moody_friction_factor",
            reynolds="100000", roughness="0.00015", diameter="0.1",
        )
        # ε/D = 1.5e-3; expected f ≈ 0.0237
        assert Decimal(r["friction_factor"]) > Decimal("0.022")
        assert Decimal(r["friction_factor"]) < Decimal("0.025")

    def test_zero_reynolds_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.moody_friction_factor",
                reynolds="0", roughness="0", diameter="0.1",
            )

    def test_negative_roughness_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.moody_friction_factor",
                reynolds="10000", roughness="-1", diameter="0.1",
            )


class TestHazenWilliamsFlow:
    def test_basic(self) -> None:
        r = REGISTRY.invoke(
            "engineering.hazen_williams_flow",
            coefficient="120", diameter="0.3", head_loss="5", length="100",
        )
        assert Decimal(r["flow_rate_m3s"]) > Decimal("0")

    def test_zero_slope_gives_zero_flow(self) -> None:
        r = REGISTRY.invoke(
            "engineering.hazen_williams_flow",
            coefficient="120", diameter="0.3", head_loss="0", length="100",
        )
        assert Decimal(r["flow_rate_m3s"]) == Decimal("0")

    def test_zero_coefficient_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.hazen_williams_flow",
                coefficient="0", diameter="0.3", head_loss="5", length="100",
            )

    def test_zero_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.hazen_williams_flow",
                coefficient="120", diameter="0.3", head_loss="5", length="0",
            )


class TestPumpHydraulicPower:
    def test_basic(self) -> None:
        """ρ=1000, g=9.80665, Q=0.1, H=20 → P = 19613.3 W."""
        r = REGISTRY.invoke(
            "engineering.pump_hydraulic_power",
            density="1000", flow_rate="0.1", head="20",
        )
        _assert_close(r["hydraulic_power_w"], Decimal("19613.3"), tol=Decimal("1"))

    def test_with_efficiency(self) -> None:
        r = REGISTRY.invoke(
            "engineering.pump_hydraulic_power",
            density="1000", flow_rate="0.1", head="20", efficiency="0.7",
        )
        assert "shaft_power_w" in r
        # Shaft > hydraulic
        assert Decimal(r["shaft_power_w"]) > Decimal(r["hydraulic_power_w"])

    def test_zero_flow_gives_zero_power(self) -> None:
        r = REGISTRY.invoke(
            "engineering.pump_hydraulic_power",
            density="1000", flow_rate="0", head="20",
        )
        assert Decimal(r["hydraulic_power_w"]) == Decimal("0")

    def test_invalid_efficiency_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.pump_hydraulic_power",
                density="1000", flow_rate="0.1", head="20", efficiency="1.5",
            )

    def test_zero_density_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.pump_hydraulic_power",
                density="0", flow_rate="0.1", head="20",
            )


class TestFluidConcurrency:
    def test_moody_batch_race_free(self) -> None:
        """engineering.moody_friction_factor must be thread-safe under N=100."""
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.moody_friction_factor",
                reynolds=str(1000 + n),
                roughness="0",
                diameter="0.1",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for res in results:
            assert "friction_factor" in res
            assert Decimal(res["friction_factor"]) > Decimal("0")
