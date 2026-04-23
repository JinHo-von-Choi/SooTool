"""Tests for finance.var_historical, var_parametric, sharpe, sortino."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestHistoricalVaR:
    def test_95pct_var(self):
        """10개 수익률 중 5%분위수 = 최악 손실."""
        r = REGISTRY.invoke(
            "finance.var_historical",
            returns=["-0.10","-0.05","-0.02","0","0.01","0.02","0.03","0.04","0.05","0.06"],
            confidence="0.95",
        )
        assert float(r["var"]) > 0

    def test_cvar_ge_var(self):
        r = REGISTRY.invoke(
            "finance.var_historical",
            returns=["-0.10","-0.05","-0.02","0","0.01","0.02","0.03","0.04","0.05","0.06"],
            confidence="0.95",
        )
        assert Decimal(r["cvar"]) >= Decimal(r["var"])

    def test_invalid_confidence_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.var_historical", returns=["-0.1","0.1"], confidence="1.5")

    def test_small_sample_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("finance.var_historical", returns=["-0.1"])


class TestParametricVaR:
    def test_gaussian_assumption(self):
        r = REGISTRY.invoke(
            "finance.var_parametric",
            returns=["-0.02","-0.01","0","0.01","0.02","0.01","0","-0.01"],
            confidence="0.95",
        )
        assert float(r["var"]) > 0
        assert "mu" in r
        assert "sigma" in r

    def test_trace(self):
        r = REGISTRY.invoke("finance.var_parametric", returns=["-0.02","0.02"])
        assert r["trace"]["tool"] == "finance.var_parametric"


class TestSharpe:
    def test_basic(self):
        r = REGISTRY.invoke(
            "finance.sharpe_ratio",
            returns=["0.01","0.02","-0.01","0.03","0.01","0.02"],
            risk_free_rate="0",
        )
        assert float(r["sharpe"]) > 0

    def test_annualized(self):
        r = REGISTRY.invoke(
            "finance.sharpe_ratio",
            returns=["0.01","0.02","-0.01","0.03","0.01","0.02"],
            periods_per_year=252,
        )
        assert r["annualized"] is not None

    def test_zero_stdev_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.sharpe_ratio",
                returns=["0.01","0.01","0.01"],
            )


class TestSortino:
    def test_basic(self):
        r = REGISTRY.invoke(
            "finance.sortino_ratio",
            returns=["0.01","0.02","-0.01","0.03","0.01","-0.02"],
            risk_free_rate="0",
        )
        assert "sortino" in r

    def test_no_downside_raises(self):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.sortino_ratio",
                returns=["0.01","0.02","0.03","0.04"],
            )
