"""Tests for math.integrate_simpson and math.integrate_gauss_legendre."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.math  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestSimpson:
    def test_polynomial_x_squared(self) -> None:
        # ∫₀³ x² dx = 9
        r = REGISTRY.invoke("math.integrate_simpson", expression="x*x", a="0", b="3", n=100)
        assert abs(Decimal(r["result"]) - Decimal("9")) < Decimal("1E-6")

    def test_sin_on_pi(self) -> None:
        # ∫₀^π sin(x) dx = 2
        r = REGISTRY.invoke(
            "math.integrate_simpson", expression="sin(x)", a="0", b="3.141592653589793", n=200
        )
        assert abs(Decimal(r["result"]) - Decimal("2")) < Decimal("1E-6")

    def test_invalid_n_odd_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("math.integrate_simpson", expression="x", a="0", b="1", n=3)

    def test_a_ge_b_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("math.integrate_simpson", expression="x", a="2", b="1", n=10)


class TestGaussLegendre:
    def test_polynomial_x_squared(self) -> None:
        r = REGISTRY.invoke(
            "math.integrate_gauss_legendre", expression="x*x", a="0", b="3", degree=10,
        )
        assert abs(Decimal(r["result"]) - Decimal("9")) < Decimal("1E-6")

    def test_degree_invalid_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "math.integrate_gauss_legendre", expression="x", a="0", b="1", degree=1,
            )


class TestBatchRaceFree:
    def test_integrate_simpson_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "math.integrate_simpson", expression="x*x", a="0", b="3", n=100,
        )["result"]

        def run() -> str:
            return REGISTRY.invoke(
                "math.integrate_simpson", expression="x*x", a="0", b="3", n=100,
            )["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline


class TestTrace:
    def test_simpson_trace_present(self) -> None:
        r = REGISTRY.invoke("math.integrate_simpson", expression="x", a="0", b="1", n=10)
        assert r["trace"]["tool"] == "math.integrate_simpson"
        assert "formula" in r["trace"]
