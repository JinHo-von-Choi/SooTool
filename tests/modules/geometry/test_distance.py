"""Tests for geometry.haversine distance tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.geometry  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _haversine(
    lat1: str, lon1: str,
    lat2: str, lon2: str,
    earth_radius_km: str = "6371",
) -> dict:
    return REGISTRY.invoke(
        "geometry.haversine",
        lat1=lat1, lon1=lon1,
        lat2=lat2, lon2=lon2,
        earth_radius_km=earth_radius_km,
    )


class TestHaversine:
    def test_same_point_zero_distance(self) -> None:
        result = _haversine("37.5665", "126.9780", "37.5665", "126.9780")
        assert Decimal(result["distance_km"]) == Decimal("0")

    def test_seoul_busan_approx_325km(self) -> None:
        # Seoul: 37.5665°N, 126.9780°E
        # Busan: 35.1796°N, 129.0756°E
        # Expected: approximately 325 km (great-circle)
        result = _haversine("37.5665", "126.9780", "35.1796", "129.0756")
        dist = Decimal(result["distance_km"])
        assert Decimal("310") < dist < Decimal("340"), (
            f"Seoul–Busan distance expected ~325 km, got {dist}"
        )

    def test_equator_10_degrees_longitude(self) -> None:
        # On the equator, 1° longitude ≈ 111.32 km
        # 10° ≈ 1113.2 km
        result = _haversine("0", "0", "0", "10")
        dist = Decimal(result["distance_km"])
        assert Decimal("1100") < dist < Decimal("1130")

    def test_north_to_south_pole(self) -> None:
        # Distance from N pole to S pole = half circumference = π*R ≈ 20015 km
        result = _haversine("90", "0", "-90", "0")
        dist = Decimal(result["distance_km"])
        assert Decimal("20000") < dist < Decimal("20030")

    def test_custom_radius(self) -> None:
        # Unit sphere: R=1, should return radian distance for 90° apart
        result = _haversine("0", "0", "0", "90", earth_radius_km="1")
        dist = Decimal(result["distance_km"])
        # 90° apart on equator = π/2 radians ≈ 1.5707...
        assert abs(dist - Decimal("1.5707963")) < Decimal("0.0001")

    def test_symmetry(self) -> None:
        # Distance A→B == B→A
        r1 = _haversine("37.5665", "126.9780", "35.1796", "129.0756")
        r2 = _haversine("35.1796", "129.0756", "37.5665", "126.9780")
        assert abs(Decimal(r1["distance_km"]) - Decimal(r2["distance_km"])) < Decimal("0.001")

    def test_trace_present(self) -> None:
        result = _haversine("0", "0", "0", "0")
        assert "trace" in result
        assert result["trace"]["tool"] == "geometry.haversine"

    def test_paris_new_york_approx(self) -> None:
        # Paris: 48.8566°N, 2.3522°E
        # New York: 40.7128°N, -74.0060°W
        # Great circle distance ≈ 5837 km
        result = _haversine("48.8566", "2.3522", "40.7128", "-74.0060")
        dist = Decimal(result["distance_km"])
        assert Decimal("5700") < dist < Decimal("5950")

    # Validation tests
    def test_invalid_lat_too_high_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _haversine("91", "0", "0", "0")

    def test_invalid_lat_too_low_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _haversine("-91", "0", "0", "0")

    def test_invalid_lon_too_high_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _haversine("0", "181", "0", "0")

    def test_invalid_radius_zero_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _haversine("0", "0", "0", "0", earth_radius_km="0")

    def test_invalid_radius_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _haversine("0", "0", "0", "0", earth_radius_km="-1")

    def test_invalid_lat_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _haversine("north", "0", "0", "0")

    # Property: triangle inequality (A→B + B→C ≥ A→C)
    def test_triangle_inequality(self) -> None:
        # Seoul, Busan, Tokyo
        ab = Decimal(_haversine("37.5665", "126.9780", "35.1796", "129.0756")["distance_km"])
        bc = Decimal(_haversine("35.1796", "129.0756", "35.6762", "139.6503")["distance_km"])
        ac = Decimal(_haversine("37.5665", "126.9780", "35.6762", "139.6503")["distance_km"])
        assert ab + bc >= ac - Decimal("0.01")  # small tolerance for float arithmetic
