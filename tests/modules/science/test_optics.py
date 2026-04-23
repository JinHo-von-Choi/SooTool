"""Tests for science optics tools: Snell, thin lens, Bragg, intensity."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.science  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestSnell:
    def test_air_to_water_30deg(self) -> None:
        # n1=1.0, n2=1.333, theta1=30 → sin_t2 = sin(30)/1.333 = 0.3751 → 22.03°
        r = REGISTRY.invoke("science.snell_law", n1="1.0", n2="1.333", theta1="30")
        assert abs(Decimal(r["theta2"]) - Decimal("22.03")) < Decimal("0.05")

    def test_total_internal_reflection_raises(self) -> None:
        # water->air at 60° > critical ~48.6°
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("science.snell_law", n1="1.5", n2="1.0", theta1="60")

    def test_rad_unit(self) -> None:
        # theta1 = pi/6 rad = 30°
        r = REGISTRY.invoke(
            "science.snell_law", n1="1", n2="1.5", theta1="0.5235987755", unit="rad",
        )
        # sin(30)/1.5 = 0.3333, asin = 0.3398 rad
        assert abs(Decimal(r["theta2"]) - Decimal("0.3398")) < Decimal("0.01")


class TestThinLens:
    def test_focal_from_pq(self) -> None:
        # 1/f = 1/30 + 1/60 = 1/20 → f=20, m=-2
        r = REGISTRY.invoke("science.thin_lens", object_dist="30", image_dist="60")
        assert Decimal(r["focal_length"]) == Decimal("20")
        assert Decimal(r["magnification"]) == Decimal("-2")

    def test_image_from_fp(self) -> None:
        # f=20, p=30 → 1/q = 1/20 - 1/30 = 1/60 → q=60
        r = REGISTRY.invoke("science.thin_lens", focal_length="20", object_dist="30")
        assert abs(Decimal(r["image_dist"]) - Decimal("60")) < Decimal("1E-8")

    def test_not_two_inputs_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("science.thin_lens", object_dist="30")


class TestBragg:
    def test_find_angle(self) -> None:
        # n=1, λ=0.154 nm, d=0.3 nm → sinθ = 0.2567, θ ≈ 14.87°
        r = REGISTRY.invoke("science.bragg", order=1, wavelength="0.154", spacing="0.3")
        assert abs(Decimal(r["angle"]) - Decimal("14.87")) < Decimal("0.05")

    def test_find_wavelength(self) -> None:
        # At angle 14.87°, nλ = 2d sinθ → λ ≈ 0.154
        r = REGISTRY.invoke("science.bragg", order=1, spacing="0.3", angle="14.87")
        assert abs(Decimal(r["wavelength"]) - Decimal("0.154")) < Decimal("0.005")

    def test_invalid_combination_raises(self) -> None:
        # None of wavelength/spacing/angle is None -> should raise
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "science.bragg", order=1, wavelength="0.1", spacing="0.3", angle="20",
            )


class TestIntensity:
    def test_100w_5m2(self) -> None:
        r = REGISTRY.invoke("science.intensity", power_w="100", area_m2="5")
        assert Decimal(r["intensity"]) == Decimal("20")
        assert r["unit"] == "W/m^2"


class TestBatchRaceFree:
    def test_snell_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "science.snell_law", n1="1", n2="1.5", theta1="30",
        )["theta2"]

        def run() -> str:
            return REGISTRY.invoke(
                "science.snell_law", n1="1", n2="1.5", theta1="30",
            )["theta2"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
