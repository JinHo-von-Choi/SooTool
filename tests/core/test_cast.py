"""
Tests for core/cast.py — boundary casting between Decimal, float64, mpmath, Quantity.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import math
from decimal import Decimal

import mpmath
import pytest

from sootool.core.cast import (
    decimal_to_float64,
    float64_to_decimal_str,
    mpmath_to_decimal,
    quantity_to_snapshot,
    snapshot_to_quantity,
)
from sootool.core.units import Q


class TestDecimalToFloat64:
    def test_basic_conversion(self):
        result = decimal_to_float64(Decimal("0.1"))
        assert result == 0.1

    def test_returns_float_type(self):
        result = decimal_to_float64(Decimal("3.14"))
        assert isinstance(result, float)

    def test_integer_decimal(self):
        result = decimal_to_float64(Decimal("100"))
        assert result == 100.0

    def test_negative(self):
        result = decimal_to_float64(Decimal("-2.5"))
        assert result == -2.5

    def test_precision_loss_logs_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="sootool.core.cast"):
            # A Decimal with many significant digits that float64 cannot represent exactly
            decimal_to_float64(Decimal("1." + "1" * 20))
        assert len(caplog.records) > 0


class TestFloat64ToDecimalStr:
    def test_basic(self):
        result = float64_to_decimal_str(0.1)
        assert result == "0.1"

    def test_not_bloated(self):
        # Must not produce "0.1000000000000000056..." style output
        result = float64_to_decimal_str(0.1)
        assert "00000000000000" not in result

    def test_custom_digits(self):
        result = float64_to_decimal_str(1.0 / 3.0, digits=6)
        assert result == "0.333333"

    def test_integer_float(self):
        result = float64_to_decimal_str(42.0)
        assert result == "42"

    def test_negative(self):
        result = float64_to_decimal_str(-1.5)
        assert result == "-1.5"


class TestMpmathToDecimal:
    def test_basic(self):
        mpmath.mp.dps = 60
        x = mpmath.mpf("0.1")
        result = mpmath_to_decimal(x)
        assert isinstance(result, Decimal)
        # Should be close to 0.1 within 50 digits
        assert abs(result - Decimal("0.1")) < Decimal("1e-40")

    def test_returns_decimal_type(self):
        result = mpmath_to_decimal(mpmath.mpf("3.14159"))
        assert isinstance(result, Decimal)

    def test_high_precision_pi(self):
        mpmath.mp.dps = 60
        pi = mpmath.pi
        result = mpmath_to_decimal(pi, digits=50)
        # Compare with known pi digits
        expected_prefix = "3.14159265358979"
        assert str(result).startswith(expected_prefix)

    def test_custom_digits(self):
        result = mpmath_to_decimal(mpmath.mpf("1") / mpmath.mpf("3"), digits=10)
        assert isinstance(result, Decimal)
        # Check approximately 10 significant digits
        assert abs(result - Decimal("1") / Decimal("3")) < Decimal("1e-9")


class TestQuantitySnapshot:
    def test_roundtrip_magnitude(self):
        q = Q("1.5", "meter")
        snapshot = quantity_to_snapshot(q)
        restored = snapshot_to_quantity(snapshot)
        assert restored.magnitude == q.magnitude

    def test_roundtrip_units(self):
        q = Q("1.5", "meter")
        snapshot = quantity_to_snapshot(q)
        restored = snapshot_to_quantity(snapshot)
        assert str(restored.units) == str(q.units)

    def test_snapshot_is_json_safe(self):
        import json
        q = Q("2.718", "kilogram")
        snapshot = quantity_to_snapshot(q)
        # Must serialize to JSON without error
        serialized = json.dumps(snapshot)
        assert '"magnitude"' in serialized
        assert '"unit"' in serialized

    def test_snapshot_keys(self):
        q = Q("100", "second")
        snapshot = quantity_to_snapshot(q)
        assert "magnitude" in snapshot
        assert "unit" in snapshot

    def test_snapshot_magnitude_is_string(self):
        q = Q("3.14", "meter")
        snapshot = quantity_to_snapshot(q)
        assert isinstance(snapshot["magnitude"], str)

    def test_singleton_ureg(self):
        """snapshot_to_quantity must use the same UnitRegistry as Q()."""
        q1 = Q("1", "meter")
        snap = quantity_to_snapshot(q1)
        q2 = snapshot_to_quantity(snap)
        # Converting between quantities from the same registry should work
        assert q2.to("centimeter").magnitude == Decimal("100")
