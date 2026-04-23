"""Tests for engineering.gear_bearing tools (Tier 3)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestGearRatio:
    def test_reduction(self) -> None:
        r = REGISTRY.invoke(
            "engineering.gear_ratio",
            teeth_driver="20", teeth_driven="60",
        )
        assert Decimal(r["ratio"]) == Decimal("3")
        assert r["direction"] == "reduction"

    def test_overdrive(self) -> None:
        r = REGISTRY.invoke(
            "engineering.gear_ratio",
            teeth_driver="60", teeth_driven="20",
        )
        _assert_close(r["ratio"], Decimal(1) / Decimal(3), tol=Decimal("1E-30"))
        assert r["direction"] == "overdrive"

    def test_direct(self) -> None:
        r = REGISTRY.invoke(
            "engineering.gear_ratio",
            teeth_driver="30", teeth_driven="30",
        )
        assert r["direction"] == "direct"

    def test_zero_teeth_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.gear_ratio",
                teeth_driver="0", teeth_driven="10",
            )


class TestGearTorqueTransmission:
    def test_ideal(self) -> None:
        """τ_in=10, i=3, η=1 → τ_out=30."""
        r = REGISTRY.invoke(
            "engineering.gear_torque_transmission",
            input_torque="10", teeth_driver="20", teeth_driven="60",
            efficiency="1",
        )
        assert Decimal(r["output_torque"]) == Decimal("30")

    def test_with_efficiency(self) -> None:
        """η=0.9 → τ_out = 10·3·0.9 = 27."""
        r = REGISTRY.invoke(
            "engineering.gear_torque_transmission",
            input_torque="10", teeth_driver="20", teeth_driven="60",
            efficiency="0.9",
        )
        assert Decimal(r["output_torque"]) == Decimal("27")

    def test_zero_efficiency(self) -> None:
        r = REGISTRY.invoke(
            "engineering.gear_torque_transmission",
            input_torque="100", teeth_driver="10", teeth_driven="30",
            efficiency="0",
        )
        assert Decimal(r["output_torque"]) == Decimal("0")

    def test_efficiency_over_one_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.gear_torque_transmission",
                input_torque="1", teeth_driver="1", teeth_driven="1",
                efficiency="1.1",
            )


class TestBearingLifeL10:
    def test_ball(self) -> None:
        """ball p=3; C/P=2 → L10 = 8."""
        r = REGISTRY.invoke(
            "engineering.bearing_life_l10",
            dynamic_capacity="20000", equivalent_load="10000",
            bearing_type="ball",
        )
        assert Decimal(r["l10_million_revolutions"]) == Decimal("8")
        assert r["exponent"] == "3"

    def test_roller(self) -> None:
        """roller p=10/3; C/P=2 → L10 = 2^(10/3) ≈ 10.0794."""
        r = REGISTRY.invoke(
            "engineering.bearing_life_l10",
            dynamic_capacity="20000", equivalent_load="10000",
            bearing_type="roller",
        )
        expected = 2 ** (10 / 3)
        _assert_close(r["l10_million_revolutions"], Decimal(str(expected)), tol=Decimal("1E-6"))

    def test_load_exceeds_capacity_life_under_one(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bearing_life_l10",
            dynamic_capacity="1000", equivalent_load="2000",
            bearing_type="ball",
        )
        assert Decimal(r["l10_million_revolutions"]) < Decimal("1")

    def test_zero_load_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bearing_life_l10",
                dynamic_capacity="1000", equivalent_load="0",
                bearing_type="ball",
            )

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bearing_life_l10",
                dynamic_capacity="1000", equivalent_load="100",
                bearing_type="thrust",
            )


class TestBearingEquivalentLoad:
    def test_basic(self) -> None:
        """Fr=5000, Fa=2000, X=0.56, Y=1.45 → P = 0.56·5000 + 1.45·2000 = 5700."""
        r = REGISTRY.invoke(
            "engineering.bearing_equivalent_load",
            radial_load="5000", axial_load="2000",
            x_factor="0.56", y_factor="1.45",
        )
        assert Decimal(r["equivalent_load"]) == Decimal("5700")

    def test_pure_radial(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bearing_equivalent_load",
            radial_load="3000", axial_load="0",
            x_factor="1", y_factor="0",
        )
        assert Decimal(r["equivalent_load"]) == Decimal("3000")

    def test_pure_axial(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bearing_equivalent_load",
            radial_load="0", axial_load="2000",
            x_factor="0", y_factor="2",
        )
        assert Decimal(r["equivalent_load"]) == Decimal("4000")

    def test_both_zero_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bearing_equivalent_load",
                radial_load="0", axial_load="0",
                x_factor="1", y_factor="1",
            )

    def test_negative_radial_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bearing_equivalent_load",
                radial_load="-100", axial_load="100",
                x_factor="1", y_factor="1",
            )


class TestConcurrency:
    def test_gear_ratio_batch_race_free(self) -> None:
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.gear_ratio",
                teeth_driver="10", teeth_driven=str(n * 10),
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            assert Decimal(res["ratio"]) == Decimal(n), f"mismatch at n={n}"
