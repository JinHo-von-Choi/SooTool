"""Tests for stats.mann_whitney_u, wilcoxon, kruskal_wallis."""
from __future__ import annotations

import pytest

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestMannWhitney:
    def test_clear_difference(self):
        r = REGISTRY.invoke(
            "stats.mann_whitney_u",
            a=["1","2","3","4","5"],
            b=["6","7","8","9","10"],
        )
        assert float(r["p_value"]) < 0.05
        assert r["n_a"] == 5
        assert r["n_b"] == 5

    def test_same_distribution(self):
        r = REGISTRY.invoke(
            "stats.mann_whitney_u",
            a=["1","2","3","4","5","6"],
            b=["1","2","3","4","5","6"],
        )
        assert float(r["p_value"]) > 0.05

    def test_invalid_tail_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "stats.mann_whitney_u",
                a=["1","2"], b=["3","4"], tail="invalid",
            )


class TestWilcoxon:
    def test_paired(self):
        r = REGISTRY.invoke(
            "stats.wilcoxon",
            a=["1","2","3","4","5"],
            b=["2","3","4","5","6"],
        )
        assert r["n"] == 5
        # 일관된 증가 → 검정 통계량 존재
        assert "p_value" in r

    def test_single_sample(self):
        r = REGISTRY.invoke("stats.wilcoxon", a=["-1","1","-2","2","-3","3"])
        # 대칭 → p>0.05 기대
        assert "p_value" in r

    def test_length_mismatch_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("stats.wilcoxon", a=["1","2","3"], b=["1","2"])


class TestKruskalWallis:
    def test_3_groups(self):
        r = REGISTRY.invoke(
            "stats.kruskal_wallis",
            groups=[["1","2","3"],["4","5","6"],["7","8","9"]],
        )
        assert float(r["p_value"]) < 0.05
        assert r["df"] == 2

    def test_single_group_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("stats.kruskal_wallis", groups=[["1","2"]])
