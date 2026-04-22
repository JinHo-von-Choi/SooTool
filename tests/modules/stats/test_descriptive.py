"""Tests for stats.descriptive tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call_descriptive(**kwargs):
    return REGISTRY.invoke("stats.descriptive", **kwargs)


class TestDescriptive:
    def test_stdev_ddof_default_sample(self):
        """[1,2,3,4,5] ddof=1 → sample stdev ≈ 1.5811388300842..."""
        result = call_descriptive(values=["1", "2", "3", "4", "5"])
        stdev = float(result["stdev"])
        assert abs(stdev - 1.5811388300842) < 1e-9

    def test_stdev_population_ddof_0(self):
        """[1,2,3,4,5] ddof=0 → population stdev ≈ 1.4142135623731..."""
        result = call_descriptive(values=["1", "2", "3", "4", "5"], ddof=0)
        stdev = float(result["stdev"])
        assert abs(stdev - 1.4142135623731) < 1e-9

    def test_mean_exact(self):
        result = call_descriptive(values=["2", "4", "6", "8", "10"])
        assert float(result["mean"]) == 6.0

    def test_median_odd(self):
        result = call_descriptive(values=["3", "1", "4", "1", "5"])
        # sorted: [1, 1, 3, 4, 5] → median = 3
        assert float(result["median"]) == 3.0

    def test_median_even(self):
        result = call_descriptive(values=["1", "2", "3", "4"])
        # median = (2+3)/2 = 2.5
        assert float(result["median"]) == 2.5

    def test_min_max(self):
        result = call_descriptive(values=["10", "3", "7", "1", "9"])
        assert float(result["min"]) == 1.0
        assert float(result["max"]) == 10.0

    def test_n_count(self):
        result = call_descriptive(values=["1", "2", "3", "4", "5", "6"])
        assert result["n"] == 6

    def test_q1_q3(self):
        result = call_descriptive(values=["1", "2", "3", "4", "5", "6", "7", "8"])
        q1 = float(result["q1"])
        q3 = float(result["q3"])
        assert q1 < float(result["median"]) < q3

    def test_variance_ddof1(self):
        result = call_descriptive(values=["2", "4", "4", "4", "5", "5", "7", "9"])
        var = float(result["variance"])
        # numpy ddof=1: [(2-5)²+(4-5)²+(4-5)²+(4-5)²+(5-5)²+(5-5)²+(7-5)²+(9-5)²] / 7
        # = [9+1+1+1+0+0+4+16] / 7 = 32/7 ≈ 4.5714...
        assert abs(var - 32/7) < 1e-8

    def test_output_strings_not_float(self):
        """All numeric outputs must be Decimal strings (not float)."""
        result = call_descriptive(values=["1.5", "2.5", "3.5"])
        for key in ("mean", "median", "variance", "stdev", "min", "max", "q1", "q3"):
            assert isinstance(result[key], str), f"{key} should be a string"

    def test_trace_present(self):
        result = call_descriptive(values=["1", "2", "3"])
        assert "trace" in result
        assert result["trace"]["tool"] == "stats.descriptive"


class TestDescriptiveInvalid:
    def test_n1_raises(self):
        with pytest.raises(InvalidInputError):
            call_descriptive(values=["42"])

    def test_empty_raises(self):
        with pytest.raises(InvalidInputError):
            call_descriptive(values=[])

    def test_non_numeric_raises(self):
        with pytest.raises(InvalidInputError):
            call_descriptive(values=["1", "abc", "3"])


class TestDescriptiveConcurrency:
    def test_batch_race_free(self):
        """100 parallel descriptive calls must yield identical results."""
        data = [str(i) for i in range(1, 21)]

        def run(_):
            return call_descriptive(values=data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(run, range(100)))

        means = [r["mean"] for r in results]
        assert len(set(means)) == 1, f"Non-deterministic: {set(means)}"
