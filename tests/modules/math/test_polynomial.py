"""Tests for math.polynomial_roots and math.polynomial_horner."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.math  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestRoots:
    def test_x_squared_minus_4(self) -> None:
        r = REGISTRY.invoke("math.polynomial_roots", coefficients=["1", "0", "-4"])
        reals = sorted(Decimal(root["real"]) for root in r["roots"])
        assert abs(reals[0] - Decimal("-2")) < Decimal("1E-8")
        assert abs(reals[1] - Decimal("2")) < Decimal("1E-8")
        assert r["degree"] == 2

    def test_complex_roots(self) -> None:
        # x^2 + 1 -> ±i
        r = REGISTRY.invoke("math.polynomial_roots", coefficients=["1", "0", "1"])
        assert len(r["roots"]) == 2
        imags = sorted(Decimal(root["imag"]) for root in r["roots"])
        assert abs(imags[0] - Decimal("-1")) < Decimal("1E-8")
        assert abs(imags[1] - Decimal("1")) < Decimal("1E-8")

    def test_leading_zero_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("math.polynomial_roots", coefficients=["0", "1"])


class TestHorner:
    def test_at_known_point(self) -> None:
        # (x-1)(x-2) = x² - 3x + 2 at x=3 → 2
        r = REGISTRY.invoke("math.polynomial_horner", coefficients=["1", "-3", "2"], x="3")
        assert Decimal(r["result"]) == Decimal("2")

    def test_decimal_preserves_precision(self) -> None:
        # a*x at large numbers stays exact
        r = REGISTRY.invoke(
            "math.polynomial_horner",
            coefficients=["1", "0"],  # P(x) = x
            x="123456789012345.123456",
        )
        assert Decimal(r["result"]) == Decimal("123456789012345.123456")


class TestBatchRaceFree:
    def test_roots_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "math.polynomial_roots", coefficients=["1", "0", "-4"],
        )["roots"]

        def run() -> list:
            r = REGISTRY.invoke(
                "math.polynomial_roots", coefficients=["1", "0", "-4"],
            )
            return r["roots"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
