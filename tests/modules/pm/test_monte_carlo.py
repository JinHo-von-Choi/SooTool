"""Tests for pm.monte_carlo_schedule."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.pm  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _single_task() -> list[dict[str, str]]:
    return [{"id": "t1", "optimistic": "2", "most_likely": "4", "pessimistic": "10"}]


class TestDeterminism:
    def test_same_seed_same_output(self) -> None:
        r1 = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=0,
        )
        r2 = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=0,
        )
        assert r1["p50"] == r2["p50"]
        assert r1["mean"] == r2["mean"]

    def test_different_seeds_different_output(self) -> None:
        r1 = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=0,
        )
        r2 = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=1,
        )
        # Very likely to differ with different seeds
        assert r1["p50"] != r2["p50"]


class TestPercentileOrdering:
    def test_p10_lt_p50_lt_p90(self) -> None:
        r = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=42,
        )
        p10 = Decimal(r["p10"])
        p50 = Decimal(r["p50"])
        p90 = Decimal(r["p90"])
        assert p10 < p50 < p90


class TestRangeConstraints:
    def test_invalid_pert_ordering_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "pm.monte_carlo_schedule",
                tasks=[{"id": "t1", "optimistic": "10", "most_likely": "5", "pessimistic": "3"}],
                n=1000, seed=0,
            )

    def test_n_too_small_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "pm.monte_carlo_schedule", tasks=_single_task(), n=10, seed=0,
            )

    def test_empty_tasks_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "pm.monte_carlo_schedule", tasks=[], n=1000, seed=0,
            )


class TestMultiTask:
    def test_sum_p50_greater_than_single(self) -> None:
        tasks = [
            {"id": "t1", "optimistic": "2", "most_likely": "4", "pessimistic": "10"},
            {"id": "t2", "optimistic": "3", "most_likely": "5", "pessimistic": "8"},
        ]
        r = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=tasks, n=1000, seed=0,
        )
        # Sum of two tasks should exceed single-task p50 (~4.5)
        assert Decimal(r["p50"]) > Decimal("6")


class TestBatchRaceFree:
    def test_mc_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=0,
        )["p50"]

        def run() -> str:
            return REGISTRY.invoke(
                "pm.monte_carlo_schedule", tasks=_single_task(), n=1000, seed=0,
            )["p50"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
