"""Tests for stats.anova_oneway."""
from __future__ import annotations

import pytest

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("stats.anova_oneway", **kwargs)


class TestAnova:
    def test_3_groups_significant(self):
        """3개 집단 평균 차이 뚜렷 → p<0.05"""
        r = call(groups=[
            ["1","2","3","4","5"],
            ["4","5","6","7","8"],
            ["9","10","11","12","13"],
        ])
        assert float(r["p_value"]) < 0.05
        assert r["reject_h0"] is True

    def test_identical_groups_not_significant(self):
        r = call(groups=[
            ["1","2","3","4","5"],
            ["1","2","3","4","5"],
            ["1","2","3","4","5"],
        ])
        assert float(r["p_value"]) > 0.05
        assert r["reject_h0"] is False

    def test_tukey_hsd_pairs(self):
        r = call(groups=[
            ["1","2","3","4","5"],
            ["4","5","6","7","8"],
            ["9","10","11","12","13"],
        ])
        assert "tukey_hsd" in r
        assert len(r["tukey_hsd"]) == 3  # C(3,2)

    def test_exclude_tukey(self):
        r = call(
            groups=[["1","2","3"], ["4","5","6"]],
            include_tukey=False,
        )
        assert "tukey_hsd" not in r

    def test_single_group_raises(self):
        with pytest.raises(InvalidInputError):
            call(groups=[["1","2","3"]])

    def test_small_group_raises(self):
        with pytest.raises(InvalidInputError):
            call(groups=[["1"], ["2","3"]])

    def test_invalid_alpha_raises(self):
        with pytest.raises(InvalidInputError):
            call(groups=[["1","2"],["3","4"]], alpha=1.5)

    def test_trace(self):
        r = call(groups=[["1","2","3"],["4","5","6"]])
        assert r["trace"]["tool"] == "stats.anova_oneway"
