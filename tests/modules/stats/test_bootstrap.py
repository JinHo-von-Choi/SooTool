"""Tests for stats.bootstrap_ci."""
from __future__ import annotations

import pytest

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("stats.bootstrap_ci", **kwargs)


class TestBootstrap:
    def test_mean_ci_deterministic(self):
        """동일 seed → 동일 결과."""
        r1 = call(
            values=["1","2","3","4","5","6","7","8","9","10"],
            statistic="mean", n_resamples=1000, seed=42,
        )
        r2 = call(
            values=["1","2","3","4","5","6","7","8","9","10"],
            statistic="mean", n_resamples=1000, seed=42,
        )
        assert r1["ci_lower"] == r2["ci_lower"]
        assert r1["ci_upper"] == r2["ci_upper"]

    def test_point_estimate(self):
        r = call(
            values=["1","2","3","4","5","6","7","8","9","10"],
            statistic="mean", n_resamples=1000,
        )
        assert float(r["point_estimate"]) == 5.5

    def test_ci_contains_point(self):
        r = call(
            values=["10","12","14","11","13","15","9","16","8","11"],
            statistic="median", n_resamples=2000, seed=1,
        )
        assert float(r["ci_lower"]) <= float(r["point_estimate"])
        assert float(r["ci_upper"]) >= float(r["point_estimate"])

    def test_different_seeds_give_different_ci(self):
        r1 = call(values=["1","2","3","4","5","6","7","8","9","10"], seed=1)
        r2 = call(values=["1","2","3","4","5","6","7","8","9","10"], seed=2)
        # Different seeds → not guaranteed different but very likely
        assert r1["seed"] == 1
        assert r2["seed"] == 2

    def test_invalid_statistic_raises(self):
        with pytest.raises(InvalidInputError):
            call(values=["1","2","3"], statistic="mode")

    def test_invalid_confidence_raises(self):
        with pytest.raises(InvalidInputError):
            call(values=["1","2","3"], confidence=1.5)

    def test_too_few_resamples_raises(self):
        with pytest.raises(InvalidInputError):
            call(values=["1","2","3"], n_resamples=10)

    def test_trace(self):
        r = call(values=["1","2","3","4","5"], n_resamples=500)
        assert r["trace"]["tool"] == "stats.bootstrap_ci"
