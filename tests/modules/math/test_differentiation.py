"""Tests for math.diff_central and math.diff_five_point."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.math  # noqa: F401
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY


class TestDiffCentral:
    def test_cos_at_zero(self) -> None:
        # d/dx cos(x) at x=0 = 0
        r = REGISTRY.invoke("math.diff_central", expression="cos(x)", x="0")
        assert abs(Decimal(r["result"])) < Decimal("1E-6")

    def test_x_squared_at_2(self) -> None:
        # d/dx x² at 2 = 4
        r = REGISTRY.invoke("math.diff_central", expression="x*x", x="2", h="0.0001")
        assert abs(Decimal(r["result"]) - Decimal("4")) < Decimal("1E-4")

    def test_negative_h_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("math.diff_central", expression="x", x="1", h="-0.01")


class TestDiffFivePoint:
    def test_sin_at_zero(self) -> None:
        # d/dx sin(x) at x=0 = 1 (high accuracy)
        r = REGISTRY.invoke("math.diff_five_point", expression="sin(x)", x="0", h="0.01")
        assert abs(Decimal(r["result"]) - Decimal("1")) < Decimal("1E-8")


class TestBatchRaceFree:
    def test_diff_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "math.diff_central", expression="x*x*x", x="2",
        )["result"]

        def run() -> str:
            return REGISTRY.invoke(
                "math.diff_central", expression="x*x*x", x="2",
            )["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
