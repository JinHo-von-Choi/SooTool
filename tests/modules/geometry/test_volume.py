"""Tests for geometry volume tools."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest

import sootool.modules.geometry  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _sphere(radius: str) -> dict:
    return REGISTRY.invoke("geometry.volume_sphere", radius=radius)


def _cylinder(radius: str, height: str) -> dict:
    return REGISTRY.invoke("geometry.volume_cylinder", radius=radius, height=height)


def _cuboid(length: str, width: str, height: str) -> dict:
    return REGISTRY.invoke("geometry.volume_cuboid", length=length, width=width, height=height)


class TestVolumeSphere:
    def test_volume_sphere_r5(self) -> None:
        result = _sphere("5")
        vol = Decimal(result["volume"])
        # (4/3)*π*125 ≈ 523.5987...
        assert abs(vol - Decimal("523.5987")) < Decimal("0.0001")

    def test_volume_sphere_r1(self) -> None:
        result = _sphere("1")
        vol = Decimal(result["volume"])
        expected = Decimal(str(4 * math.pi / 3))
        assert abs(vol - expected) < Decimal("1E-8")

    def test_volume_sphere_r0(self) -> None:
        result = _sphere("0")
        assert Decimal(result["volume"]) == Decimal("0")

    def test_volume_sphere_trace(self) -> None:
        result = _sphere("5")
        assert result["trace"]["tool"] == "geometry.volume_sphere"

    def test_volume_sphere_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _sphere("-1")

    def test_volume_sphere_invalid_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _sphere("abc")


class TestVolumeCylinder:
    def test_volume_cylinder_r3_h5(self) -> None:
        result = _cylinder("3", "5")
        vol = Decimal(result["volume"])
        expected = Decimal(str(math.pi * 9 * 5))
        assert abs(vol - expected) < Decimal("1E-8")

    def test_volume_cylinder_r1_h1(self) -> None:
        result = _cylinder("1", "1")
        vol = Decimal(result["volume"])
        expected = Decimal(str(math.pi))
        assert abs(vol - expected) < Decimal("1E-8")

    def test_volume_cylinder_r0(self) -> None:
        result = _cylinder("0", "5")
        assert Decimal(result["volume"]) == Decimal("0")

    def test_volume_cylinder_trace(self) -> None:
        result = _cylinder("3", "5")
        assert result["trace"]["tool"] == "geometry.volume_cylinder"

    def test_volume_cylinder_negative_radius_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _cylinder("-1", "5")

    def test_volume_cylinder_negative_height_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _cylinder("3", "-5")


class TestVolumeCuboid:
    def test_volume_cuboid_2_3_4(self) -> None:
        result = _cuboid("2", "3", "4")
        assert Decimal(result["volume"]) == Decimal("24")

    def test_volume_cuboid_unit(self) -> None:
        result = _cuboid("1", "1", "1")
        assert Decimal(result["volume"]) == Decimal("1")

    def test_volume_cuboid_decimal(self) -> None:
        result = _cuboid("2.5", "3", "4")
        assert Decimal(result["volume"]) == Decimal("30")

    def test_volume_cuboid_zero_dimension(self) -> None:
        result = _cuboid("0", "3", "4")
        assert Decimal(result["volume"]) == Decimal("0")

    def test_volume_cuboid_trace(self) -> None:
        result = _cuboid("2", "3", "4")
        assert result["trace"]["tool"] == "geometry.volume_cuboid"

    def test_volume_cuboid_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _cuboid("-1", "3", "4")

    # Property: cuboid volume is commutative in dimensions
    def test_volume_cuboid_commutativity(self) -> None:
        v1 = _cuboid("2", "3", "4")["volume"]
        v2 = _cuboid("4", "2", "3")["volume"]
        v3 = _cuboid("3", "4", "2")["volume"]
        assert v1 == v2 == v3
