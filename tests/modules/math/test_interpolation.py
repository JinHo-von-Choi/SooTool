"""Tests for math.interpolate_linear and math.interpolate_cubic_spline."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.math  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestLinear:
    def test_midpoint(self) -> None:
        r = REGISTRY.invoke(
            "math.interpolate_linear",
            xs=["0", "1", "2"], ys=["0", "10", "20"], x_query="1.5",
        )
        assert abs(Decimal(r["result"]) - Decimal("15")) < Decimal("1E-8")

    def test_endpoint(self) -> None:
        r = REGISTRY.invoke(
            "math.interpolate_linear",
            xs=["0", "1"], ys=["5", "8"], x_query="1",
        )
        assert Decimal(r["result"]) == Decimal("8")

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "math.interpolate_linear",
                xs=["0", "1"], ys=["0", "1"], x_query="2",
            )

    def test_len_mismatch_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "math.interpolate_linear",
                xs=["0", "1", "2"], ys=["0", "1"], x_query="0.5",
            )


class TestCubicSpline:
    def test_cubic_on_linear_data(self) -> None:
        # Linear interpolation approximated by cubic spline should match exactly on grid.
        r = REGISTRY.invoke(
            "math.interpolate_cubic_spline",
            xs=["0", "1", "2", "3"], ys=["0", "2", "4", "6"], x_query="1.5",
        )
        # Linear ys = 2x, at 1.5 -> 3
        assert abs(Decimal(r["result"]) - Decimal("3")) < Decimal("1E-8")

    def test_too_few_points_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "math.interpolate_cubic_spline",
                xs=["0", "1"], ys=["0", "1"], x_query="0.5",
            )


class TestBatchRaceFree:
    def test_interp_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "math.interpolate_linear",
            xs=["0", "1", "2"], ys=["0", "10", "20"], x_query="1.5",
        )["result"]

        def run() -> str:
            return REGISTRY.invoke(
                "math.interpolate_linear",
                xs=["0", "1", "2"], ys=["0", "10", "20"], x_query="1.5",
            )["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
