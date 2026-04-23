"""Tests for engineering.reliability tools (Tier 3)."""
from __future__ import annotations

import concurrent.futures
import math
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestExponentialReliability:
    def test_mtbf_basic(self) -> None:
        """λ=0.001/h → MTBF=1000 h."""
        r = REGISTRY.invoke(
            "engineering.exponential_reliability",
            failure_rate="0.001", time="0",
        )
        assert Decimal(r["mtbf"]) == Decimal("1000")
        assert Decimal(r["reliability"]) == Decimal("1")

    def test_reliability_at_mtbf(self) -> None:
        """t = MTBF → R = 1/e ≈ 0.3679."""
        r = REGISTRY.invoke(
            "engineering.exponential_reliability",
            failure_rate="0.001", time="1000",
        )
        _assert_close(r["reliability"], Decimal(str(math.exp(-1))), tol=Decimal("1E-15"))

    def test_unreliability_plus_reliability(self) -> None:
        r = REGISTRY.invoke(
            "engineering.exponential_reliability",
            failure_rate="0.01", time="50",
        )
        total = Decimal(r["reliability"]) + Decimal(r["unreliability"])
        _assert_close(str(total), Decimal("1"), tol=Decimal("1E-20"))

    def test_zero_lambda_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.exponential_reliability",
                failure_rate="0", time="100",
            )

    def test_negative_time_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.exponential_reliability",
                failure_rate="0.01", time="-10",
            )


class TestSeriesReliability:
    def test_basic(self) -> None:
        """R1=0.9, R2=0.95, R3=0.99 → 0.84645."""
        r = REGISTRY.invoke(
            "engineering.series_reliability",
            component_reliabilities=["0.9", "0.95", "0.99"],
        )
        _assert_close(r["reliability"], Decimal("0.84645"), tol=Decimal("1E-10"))

    def test_single_component(self) -> None:
        r = REGISTRY.invoke(
            "engineering.series_reliability",
            component_reliabilities=["0.8"],
        )
        assert Decimal(r["reliability"]) == Decimal("0.8")

    def test_one_failure_destroys_series(self) -> None:
        r = REGISTRY.invoke(
            "engineering.series_reliability",
            component_reliabilities=["0.99", "0", "0.99"],
        )
        assert Decimal(r["reliability"]) == Decimal("0")

    def test_empty_list_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.series_reliability",
                component_reliabilities=[],
            )

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.series_reliability",
                component_reliabilities=["1.1"],
            )


class TestParallelReliability:
    def test_basic(self) -> None:
        """Two parallel 0.9 → R = 1 − 0.01 = 0.99."""
        r = REGISTRY.invoke(
            "engineering.parallel_reliability",
            component_reliabilities=["0.9", "0.9"],
        )
        _assert_close(r["reliability"], Decimal("0.99"), tol=Decimal("1E-30"))

    def test_single_component_is_itself(self) -> None:
        r = REGISTRY.invoke(
            "engineering.parallel_reliability",
            component_reliabilities=["0.7"],
        )
        _assert_close(r["reliability"], Decimal("0.7"), tol=Decimal("1E-30"))

    def test_one_guaranteed_makes_system_reliable(self) -> None:
        r = REGISTRY.invoke(
            "engineering.parallel_reliability",
            component_reliabilities=["0.5", "1"],
        )
        assert Decimal(r["reliability"]) == Decimal("1")

    def test_empty_list_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.parallel_reliability",
                component_reliabilities=[],
            )


class TestWeibullReliability:
    def test_time_zero(self) -> None:
        """t=0 → R=1 by convention."""
        r = REGISTRY.invoke(
            "engineering.weibull_reliability",
            shape="2", scale="1000", time="0",
        )
        assert Decimal(r["reliability"]) == Decimal("1")

    def test_at_scale_parameter(self) -> None:
        """t = η → R = exp(−1) for any β."""
        r = REGISTRY.invoke(
            "engineering.weibull_reliability",
            shape="2.5", scale="1000", time="1000",
        )
        _assert_close(r["reliability"], Decimal(str(math.exp(-1))), tol=Decimal("1E-15"))

    def test_beta_equals_one_matches_exponential(self) -> None:
        """β=1 → Weibull == 지수. λ = 1/η = 0.01, t=50 → R=exp(−0.5)."""
        r = REGISTRY.invoke(
            "engineering.weibull_reliability",
            shape="1", scale="100", time="50",
        )
        _assert_close(r["reliability"], Decimal(str(math.exp(-0.5))), tol=Decimal("1E-15"))

    def test_high_shape_steep_dropoff(self) -> None:
        """β=10, t=2η → R = exp(−2^10) → ~0."""
        r = REGISTRY.invoke(
            "engineering.weibull_reliability",
            shape="10", scale="1", time="2",
        )
        assert Decimal(r["reliability"]) < Decimal("1E-400")

    def test_zero_shape_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.weibull_reliability",
                shape="0", scale="100", time="50",
            )

    def test_zero_scale_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.weibull_reliability",
                shape="2", scale="0", time="50",
            )


class TestConcurrency:
    def test_exponential_batch_race_free(self) -> None:
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.exponential_reliability",
                failure_rate=str(Decimal(1) / Decimal(n)),
                time="0",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            _assert_close(res["mtbf"], Decimal(n), tol=Decimal("1E-20"))
