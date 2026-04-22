"""Tests for engineering.fluid_reynolds tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401  — triggers REGISTRY auto-registration
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


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
