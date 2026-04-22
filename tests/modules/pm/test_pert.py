"""Tests for PM PERT tool."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.pm  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _pert(o: str, m: str, p: str) -> dict:
    return REGISTRY.invoke("pm.pert", optimistic=o, most_likely=m, pessimistic=p)


class TestPERT:
    def test_pert_symmetric(self) -> None:
        """O=2, M=4, P=6: E=4, variance=((6-2)/6)^2 = (4/6)^2 = 16/36 = 4/9."""
        r = _pert("2", "4", "6")
        expected_e = Decimal("4")
        expected_v = Decimal("4") / Decimal("9")

        assert abs(Decimal(r["expected"]) - expected_e) < Decimal("1E-9")
        assert abs(Decimal(r["variance"]) - expected_v) < Decimal("1E-9")

    def test_pert_stdev_sqrt_variance(self) -> None:
        """stdev = sqrt(variance)."""
        r = _pert("2", "4", "6")
        var   = Decimal(r["variance"])
        stdev = Decimal(r["stdev"])
        assert abs(stdev * stdev - var) < Decimal("1E-10")

    def test_pert_equal_estimates(self) -> None:
        """O=M=P: E=M, variance=0, stdev=0."""
        r = _pert("5", "5", "5")
        assert Decimal(r["expected"]) == Decimal("5")
        assert Decimal(r["variance"]) == Decimal("0")
        assert Decimal(r["stdev"])    == Decimal("0")

    def test_pert_most_likely_weighted(self) -> None:
        """Most likely is weighted 4x in the formula."""
        # E = (1 + 4*5 + 9) / 6 = (1 + 20 + 9) / 6 = 30/6 = 5
        r = _pert("1", "5", "9")
        assert abs(Decimal(r["expected"]) - Decimal("5")) < Decimal("1E-9")

    def test_pert_optimistic_gt_pessimistic_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _pert("10", "5", "3")

    def test_pert_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _pert("abc", "5", "10")

    def test_pert_variance_formula_explicit(self) -> None:
        """V = ((P-O)/6)^2 = ((10-2)/6)^2 = (8/6)^2 = 64/36."""
        r = _pert("2", "6", "10")
        expected_v = (Decimal("10") - Decimal("2")) ** 2 / Decimal("36")
        assert abs(Decimal(r["variance"]) - expected_v) < Decimal("1E-9")

    def test_pert_trace_present(self) -> None:
        r = _pert("1", "3", "5")
        assert "trace" in r
        assert r["trace"]["tool"] == "pm.pert"

    def test_pert_large_values(self) -> None:
        """Large duration values must not overflow."""
        r = _pert("100", "500", "1000")
        expected_e = (Decimal("100") + Decimal("4") * Decimal("500") + Decimal("1000")) / Decimal("6")
        assert abs(Decimal(r["expected"]) - expected_e) < Decimal("1E-6")


class TestPERTBatchRaceFree:
    def test_pm_batch_race_free(self) -> None:
        expected_e = _pert("2", "4", "6")["expected"]

        def run() -> str:
            return _pert("2", "4", "6")["expected"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == expected_e, f"Race condition in pert"
