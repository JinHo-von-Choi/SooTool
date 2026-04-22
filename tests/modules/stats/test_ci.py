"""Tests for stats.ci_mean tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

import numpy as np
import pytest
import scipy.stats as scipy_stats

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call_ci_mean(**kwargs):
    return REGISTRY.invoke("stats.ci_mean", **kwargs)


class TestCiMean:
    def test_ci_mean_95_known_data(self):
        """Verify against scipy.stats.t.interval directly."""
        data = ["10", "12", "11", "13", "9", "14", "10", "12", "11"]
        arr  = [float(x) for x in data]
        n    = len(arr)
        mean_val = float(np.mean(arr))
        se       = float(scipy_stats.sem(arr))
        ref_lo, ref_hi = scipy_stats.t.interval(0.95, df=n-1, loc=mean_val, scale=se)

        result = call_ci_mean(values=data, confidence="0.95")

        assert abs(float(result["lower"]) - ref_lo) < 1e-6
        assert abs(float(result["upper"]) - ref_hi) < 1e-6
        assert abs(float(result["mean"]) - mean_val) < 1e-6

    def test_ci_90(self):
        """90% CI is narrower than 95% CI for the same data."""
        data    = ["5", "7", "6", "8", "5", "9"]
        r95     = call_ci_mean(values=data, confidence="0.95")
        r90     = call_ci_mean(values=data, confidence="0.90")
        width95 = float(r95["upper"]) - float(r95["lower"])
        width90 = float(r90["upper"]) - float(r90["lower"])
        assert width90 < width95

    def test_ci_contains_mean(self):
        data   = ["1", "2", "3", "4", "5"]
        result = call_ci_mean(values=data)
        lower  = float(result["lower"])
        upper  = float(result["upper"])
        mean   = float(result["mean"])
        assert lower < mean < upper

    def test_invalid_confidence_above_1(self):
        with pytest.raises(InvalidInputError):
            call_ci_mean(values=["1", "2", "3"], confidence="1.5")

    def test_invalid_confidence_zero(self):
        with pytest.raises(InvalidInputError):
            call_ci_mean(values=["1", "2", "3"], confidence="0")

    def test_too_few_samples(self):
        with pytest.raises(InvalidInputError):
            call_ci_mean(values=["5"])

    def test_output_strings(self):
        result = call_ci_mean(values=["1", "2", "3", "4", "5"])
        assert isinstance(result["mean"], str)
        assert isinstance(result["lower"], str)
        assert isinstance(result["upper"], str)
