"""Tests for stats.cohens_d and stats.eta_squared."""
from __future__ import annotations

import pytest

import sootool.modules.stats  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestCohensD:
    def test_symmetric_sign(self):
        """a<b → d<0."""
        r = REGISTRY.invoke(
            "stats.cohens_d",
            a=["1","2","3","4","5"],
            b=["3","4","5","6","7"],
        )
        assert float(r["d"]) < 0

    def test_large_effect(self):
        r = REGISTRY.invoke(
            "stats.cohens_d",
            a=["1","2","1","2","1","2"],
            b=["10","11","10","11","10","11"],
        )
        assert float(r["d"]) < -3.0  # 매우 큰 음 효과크기

    def test_hedges_g_smaller_magnitude(self):
        """Hedges g = d * J, J < 1 → |g| <= |d|"""
        r = REGISTRY.invoke(
            "stats.cohens_d",
            a=["1","2","3","4","5"],
            b=["2","3","4","5","6"],
        )
        assert abs(float(r["hedges_g"])) <= abs(float(r["d"]))

    def test_small_sample_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("stats.cohens_d", a=["1"], b=["2","3"])

    def test_zero_pooled_stdev_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "stats.cohens_d",
                a=["1","1","1","1","1"],
                b=["2","2","2","2","2"],
            )


class TestEtaSquared:
    def test_significant_effect(self):
        r = REGISTRY.invoke(
            "stats.eta_squared",
            groups=[
                ["1","2","3","4","5"],
                ["5","6","7","8","9"],
                ["10","11","12","13","14"],
            ],
        )
        # 뚜렷한 집단차 → eta^2 > 0.5
        assert float(r["eta_squared"]) > 0.5

    def test_no_effect(self):
        r = REGISTRY.invoke(
            "stats.eta_squared",
            groups=[
                ["1","2","3","4","5"],
                ["1","2","3","4","5"],
            ],
        )
        # 집단 간 차이 없음 → eta² = 0
        assert float(r["eta_squared"]) == 0

    def test_omega_smaller_than_eta(self):
        r = REGISTRY.invoke(
            "stats.eta_squared",
            groups=[
                ["1","2","3","4","5"],
                ["2","3","4","5","6"],
                ["3","4","5","6","7"],
            ],
        )
        assert float(r["omega_squared"]) <= float(r["eta_squared"])

    def test_single_group_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("stats.eta_squared", groups=[["1","2","3"]])
