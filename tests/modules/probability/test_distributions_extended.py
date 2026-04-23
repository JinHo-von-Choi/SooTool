"""Tests for extended probability distributions: gamma, beta, exponential,
lognormal, chi-square, F (Tier B)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.probability  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_TOL = Decimal("1E-8")


class TestGamma:
    def test_gamma_pdf_exponential_special_case(self) -> None:
        # Gamma(shape=1, scale=1/λ) == Exponential(λ)
        r = REGISTRY.invoke("probability.gamma_pdf", x="1", shape="1", scale="1")
        expected = Decimal("0.3678794412")  # e^-1
        assert abs(Decimal(r["result"]) - expected) < _TOL

    def test_gamma_cdf_at_zero(self) -> None:
        r = REGISTRY.invoke("probability.gamma_cdf", x="0", shape="2", scale="1")
        assert Decimal(r["result"]) == Decimal("0")

    def test_gamma_ppf_inverse(self) -> None:
        cdf = REGISTRY.invoke("probability.gamma_cdf", x="3", shape="2", scale="1")["result"]
        ppf = REGISTRY.invoke("probability.gamma_ppf", q=cdf, shape="2", scale="1")["result"]
        assert abs(Decimal(ppf) - Decimal("3")) < Decimal("1E-6")

    def test_gamma_pdf_negative_x_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("probability.gamma_pdf", x="-1", shape="2", scale="1")

    def test_gamma_pdf_shape_zero_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("probability.gamma_pdf", x="1", shape="0", scale="1")

    def test_gamma_trace(self) -> None:
        r = REGISTRY.invoke("probability.gamma_cdf", x="1", shape="2", scale="1")
        assert r["trace"]["tool"] == "probability.gamma_cdf"


class TestBeta:
    def test_beta_cdf_symmetric_at_half(self) -> None:
        r = REGISTRY.invoke("probability.beta_cdf", x="0.5", alpha="2", beta="2")
        assert abs(Decimal(r["result"]) - Decimal("0.5")) < _TOL

    def test_beta_pdf_uniform(self) -> None:
        # Beta(1,1) == Uniform(0,1), pdf == 1
        r = REGISTRY.invoke("probability.beta_pdf", x="0.3", alpha="1", beta="1")
        assert abs(Decimal(r["result"]) - Decimal("1")) < _TOL

    def test_beta_ppf_inverse(self) -> None:
        cdf = REGISTRY.invoke("probability.beta_cdf", x="0.7", alpha="2", beta="3")["result"]
        ppf = REGISTRY.invoke("probability.beta_ppf", q=cdf, alpha="2", beta="3")["result"]
        assert abs(Decimal(ppf) - Decimal("0.7")) < Decimal("1E-6")

    def test_beta_out_of_range_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("probability.beta_pdf", x="1.5", alpha="2", beta="2")


class TestExponential:
    def test_exponential_cdf_at_mean(self) -> None:
        # CDF at x=1/λ for λ=1 is 1 - e^-1
        r = REGISTRY.invoke("probability.exponential_cdf", x="1", rate="1")
        assert abs(Decimal(r["result"]) - Decimal("0.6321205588")) < _TOL

    def test_exponential_pdf_at_zero(self) -> None:
        # f(0; λ=2) = 2
        r = REGISTRY.invoke("probability.exponential_pdf", x="0", rate="2")
        assert abs(Decimal(r["result"]) - Decimal("2")) < _TOL

    def test_exponential_ppf_median(self) -> None:
        # median = ln(2) for λ=1
        r = REGISTRY.invoke("probability.exponential_ppf", q="0.5", rate="1")
        assert abs(Decimal(r["result"]) - Decimal("0.6931471806")) < _TOL


class TestLognormal:
    def test_lognormal_cdf_at_one_std(self) -> None:
        # For mu=0, sigma=1, CDF(1) = Φ(0) = 0.5
        r = REGISTRY.invoke("probability.lognormal_cdf", x="1", mu="0", sigma="1")
        assert abs(Decimal(r["result"]) - Decimal("0.5")) < _TOL

    def test_lognormal_ppf_median(self) -> None:
        r = REGISTRY.invoke("probability.lognormal_ppf", q="0.5", mu="0", sigma="1")
        assert abs(Decimal(r["result"]) - Decimal("1")) < _TOL

    def test_lognormal_negative_x_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("probability.lognormal_pdf", x="-1", mu="0", sigma="1")


class TestChiSquare:
    def test_chi_square_cdf_critical_value(self) -> None:
        # 1 df, chi2_{0.05} = 3.841
        r = REGISTRY.invoke("probability.chi_square_cdf", x="3.8414588", df="1")
        assert abs(Decimal(r["result"]) - Decimal("0.95")) < Decimal("1E-5")

    def test_chi_square_ppf_95(self) -> None:
        r = REGISTRY.invoke("probability.chi_square_ppf", q="0.95", df="1")
        assert abs(Decimal(r["result"]) - Decimal("3.841458821")) < Decimal("1E-6")

    def test_chi_square_invalid_df_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("probability.chi_square_pdf", x="1", df="0")


class TestFDistribution:
    def test_f_ppf_known_value(self) -> None:
        # F(5, 10, 0.95) ≈ 3.3258
        r = REGISTRY.invoke("probability.f_ppf", q="0.95", dfn="5", dfd="10")
        assert abs(Decimal(r["result"]) - Decimal("3.325834829")) < Decimal("1E-5")

    def test_f_cdf_monotonic(self) -> None:
        c1 = Decimal(REGISTRY.invoke("probability.f_cdf", x="1", dfn="5", dfd="10")["result"])
        c2 = Decimal(REGISTRY.invoke("probability.f_cdf", x="3", dfn="5", dfd="10")["result"])
        assert c2 > c1


class TestBatchRaceFree:
    def test_gamma_batch_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "probability.gamma_cdf", x="2", shape="3", scale="1"
        )["result"]

        def run() -> str:
            return REGISTRY.invoke(
                "probability.gamma_cdf", x="2", shape="3", scale="1"
            )["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(100)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == baseline


class TestInvalidInputs:
    def test_gamma_invalid_q_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("probability.gamma_ppf", q="1.5", shape="2", scale="1")

    def test_beta_nonnumeric_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("probability.beta_pdf", x="abc", alpha="2", beta="2")
