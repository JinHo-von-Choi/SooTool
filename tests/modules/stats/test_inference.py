"""Tests for stats inference tools (t-tests, chi-square).

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

import pytest
import scipy.stats as scipy_stats

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call_ttest_one(**kwargs):
    return REGISTRY.invoke("stats.ttest_one_sample", **kwargs)


def call_ttest_two(**kwargs):
    return REGISTRY.invoke("stats.ttest_two_sample", **kwargs)


def call_ttest_paired(**kwargs):
    return REGISTRY.invoke("stats.ttest_paired", **kwargs)


def call_chi2(**kwargs):
    return REGISTRY.invoke("stats.chi_square_independence", **kwargs)


class TestTtestOneSample:
    def test_textbook_case(self):
        """data=[2.5,3.5,4.2,3.1,4.0], popmean=3 → verify t, df, p_value against scipy."""
        data    = ["2.5", "3.5", "4.2", "3.1", "4.0"]
        popmean = "3"

        arr     = [float(x) for x in data]
        ref     = scipy_stats.ttest_1samp(arr, popmean=3.0)

        result  = call_ttest_one(values=data, popmean=popmean)

        assert abs(float(result["t"]) - float(ref.statistic)) < 1e-4
        assert result["df"] == 4
        assert abs(float(result["p_value"]) - float(ref.pvalue)) < 1e-8

    def test_ci_95_contains_mean(self):
        data   = ["10", "12", "11", "13", "9", "11", "12"]
        result = call_ttest_one(values=data, popmean="11")
        lower  = float(result["ci_95"]["lower"])
        upper  = float(result["ci_95"]["upper"])
        import numpy as np
        mean = float(np.mean([float(x) for x in data]))
        assert lower < mean < upper

    def test_tail_greater_vs_two(self):
        """For mean > popmean, 'greater' one-sided p is approximately two-sided p/2."""
        data    = ["5", "6", "7", "5", "8"]
        # sample mean ≈ 6.2 > popmean=5 → 'greater' should yield p ≈ two-sided/2
        r_two     = call_ttest_one(values=data, popmean="5", tail="two")
        r_greater = call_ttest_one(values=data, popmean="5", tail="greater")
        p_two     = float(r_two["p_value"])
        p_greater = float(r_greater["p_value"])
        # one-sided p should be <= two-sided p
        assert p_greater <= p_two

    def test_invalid_tail(self):
        with pytest.raises(InvalidInputError):
            call_ttest_one(values=["1", "2", "3"], popmean="2", tail="both")

    def test_too_few_samples(self):
        with pytest.raises(InvalidInputError):
            call_ttest_one(values=["5"], popmean="5")


class TestTtestTwoSample:
    def test_welch_basic(self):
        a = ["10", "11", "12", "13", "11"]
        b = ["7",  "8",  "9",  "10",  "8"]

        ref_a = [float(x) for x in a]
        ref_b = [float(x) for x in b]
        ref   = scipy_stats.ttest_ind(ref_a, ref_b, equal_var=False)

        result = call_ttest_two(a=a, b=b, equal_var=False)

        assert abs(float(result["t"]) - float(ref.statistic)) < 1e-4
        assert abs(float(result["p_value"]) - float(ref.pvalue)) < 1e-8

    def test_student_equal_var(self):
        a = ["5", "6", "7"]
        b = ["4", "5", "6"]

        ref_a = [float(x) for x in a]
        ref_b = [float(x) for x in b]
        ref   = scipy_stats.ttest_ind(ref_a, ref_b, equal_var=True)

        result = call_ttest_two(a=a, b=b, equal_var=True)
        assert abs(float(result["t"]) - float(ref.statistic)) < 1e-4

    def test_ci_present(self):
        a = ["1", "2", "3", "4"]
        b = ["2", "3", "4", "5"]
        result = call_ttest_two(a=a, b=b)
        assert "lower" in result["ci_95"]
        assert "upper" in result["ci_95"]

    def test_too_few_raises(self):
        with pytest.raises(InvalidInputError):
            call_ttest_two(a=["5"], b=["3", "4"])


class TestTtestPaired:
    def test_paired_basic(self):
        """Use data where differences have actual variance."""
        a = ["2.0", "3.5", "4.1", "5.8", "6.3"]
        b = ["1.0", "2.2", "3.9", "4.5", "5.0"]

        ref_a = [float(x) for x in a]
        ref_b = [float(x) for x in b]
        ref   = scipy_stats.ttest_rel(ref_a, ref_b)

        result = call_ttest_paired(a=a, b=b)
        assert abs(float(result["t"]) - float(ref.statistic)) < 1e-4
        assert result["df"] == 4

    def test_mismatched_length_raises(self):
        with pytest.raises(InvalidInputError):
            call_ttest_paired(a=["1", "2", "3"], b=["1", "2"])


class TestChiSquare:
    def test_2x2_basic(self):
        """2x2 contingency table [[10,20],[30,15]] → df=1."""
        observed = [["10", "20"], ["30", "15"]]

        obs_arr = [[10, 20], [30, 15]]
        ref     = scipy_stats.chi2_contingency(obs_arr)

        result  = call_chi2(observed=observed)

        assert result["df"] == 1
        assert abs(float(result["chi2"]) - float(ref[0])) < 1e-6
        assert abs(float(result["p_value"]) - float(ref[1])) < 1e-8

    def test_expected_shape_matches_observed(self):
        observed = [["10", "20", "30"], ["15", "25", "10"]]
        result   = call_chi2(observed=observed)
        assert len(result["expected"]) == 2
        assert len(result["expected"][0]) == 3

    def test_expected_row_sums(self):
        """Row sums of expected should equal row sums of observed."""
        observed = [["10", "20"], ["30", "15"]]
        result   = call_chi2(observed=observed)
        obs_row0 = 10 + 20
        exp_row0 = sum(float(x) for x in result["expected"][0])
        assert abs(exp_row0 - obs_row0) < 1e-6

    def test_1x2_raises(self):
        with pytest.raises(InvalidInputError):
            call_chi2(observed=[["10", "20"]])

    def test_empty_raises(self):
        with pytest.raises(InvalidInputError):
            call_chi2(observed=[])
