"""Tests for stats.regression_linear tool.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

import random

import pytest

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call_regression(**kwargs):
    return REGISTRY.invoke("stats.regression_linear", **kwargs)


class TestRegressionLinear:
    def test_simple_perfect_fit(self):
        """y = 2*x + 3 (no noise) → coefficient ≈ 2, intercept ≈ 3, r² = 1."""
        X = [[str(i)] for i in range(10)]
        y = [str(2 * i + 3) for i in range(10)]

        result = call_regression(X=X, y=y)

        coef      = float(result["coefficients"][0])
        intercept = float(result["intercept"])
        r2        = float(result["r_squared"])

        assert abs(coef - 2.0) < 1e-6
        assert abs(intercept - 3.0) < 1e-6
        assert abs(r2 - 1.0) < 1e-6

    def test_simple_noisy_high_r2(self):
        """y ≈ 2*x + 3 with small noise → r² > 0.99."""
        rng = random.Random(42)  # noqa: S311
        X   = [[str(i)] for i in range(50)]
        y   = [str(2 * i + 3 + rng.gauss(0, 0.5)) for i in range(50)]

        result = call_regression(X=X, y=y)
        assert float(result["r_squared"]) > 0.99

    def test_multivariate(self):
        """y = 3*x1 + 5*x2 + 1 → coefficients ≈ [3, 5], intercept ≈ 1."""
        rows   = [(i, j) for i in range(1, 8) for j in range(1, 8)]
        X      = [[str(r[0]), str(r[1])] for r in rows]
        y      = [str(3 * r[0] + 5 * r[1] + 1) for r in rows]

        result = call_regression(X=X, y=y)

        coef1     = float(result["coefficients"][0])
        coef2     = float(result["coefficients"][1])
        intercept = float(result["intercept"])

        assert abs(coef1 - 3.0) < 1e-4
        assert abs(coef2 - 5.0) < 1e-4
        assert abs(intercept - 1.0) < 1e-4

    def test_no_intercept(self):
        """add_intercept=False → intercept should be 0."""
        X = [[str(i)] for i in range(1, 11)]
        y = [str(3 * i) for i in range(1, 11)]

        result = call_regression(X=X, y=y, add_intercept=False)
        assert result["intercept"] == "0"
        assert abs(float(result["coefficients"][0]) - 3.0) < 1e-6

    def test_residuals_length(self):
        X = [[str(i)] for i in range(10)]
        y = [str(i + 1) for i in range(10)]

        result = call_regression(X=X, y=y)
        assert len(result["residuals"]) == 10

    def test_p_values_length_matches_coef(self):
        X = [[str(i), str(i * 2)] for i in range(10)]
        y = [str(i + 1) for i in range(10)]

        result = call_regression(X=X, y=y)
        assert len(result["p_values"]) == len(result["coefficients"])

    def test_r_squared_between_0_and_1(self):
        X = [[str(i)] for i in range(20)]
        y = [str(i * 1.5 + 2) for i in range(20)]

        result = call_regression(X=X, y=y)
        r2 = float(result["r_squared"])
        assert 0.0 <= r2 <= 1.0

    def test_output_strings(self):
        X = [[str(i)] for i in range(5)]
        y = [str(i) for i in range(5)]

        result = call_regression(X=X, y=y)
        assert isinstance(result["intercept"], str)
        assert isinstance(result["r_squared"], str)
        assert all(isinstance(c, str) for c in result["coefficients"])

    def test_mismatched_X_y_raises(self):
        with pytest.raises(InvalidInputError):
            call_regression(
                X=[[str(i)] for i in range(5)],
                y=[str(i) for i in range(3)],
            )

    def test_empty_raises(self):
        with pytest.raises(InvalidInputError):
            call_regression(X=[], y=[])
