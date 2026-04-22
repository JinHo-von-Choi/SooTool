"""Tests for probability distribution tools: normal, binomial, Poisson."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.probability  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _npdf(x: str, mu: str = "0", sigma: str = "1") -> dict:
    return REGISTRY.invoke("probability.normal_pdf", x=x, mu=mu, sigma=sigma)


def _ncdf(x: str, mu: str = "0", sigma: str = "1") -> dict:
    return REGISTRY.invoke("probability.normal_cdf", x=x, mu=mu, sigma=sigma)


def _nppf(q: str, mu: str = "0", sigma: str = "1") -> dict:
    return REGISTRY.invoke("probability.normal_ppf", q=q, mu=mu, sigma=sigma)


def _bpmf(k: int, n: int, p: str) -> dict:
    return REGISTRY.invoke("probability.binomial_pmf", k=k, n=n, p=p)


def _bcdf(k: int, n: int, p: str) -> dict:
    return REGISTRY.invoke("probability.binomial_cdf", k=k, n=n, p=p)


def _ppmf(k: int, lam: str) -> dict:
    return REGISTRY.invoke("probability.poisson_pmf", k=k, lam=lam)


def _pcdf(k: int, lam: str) -> dict:
    return REGISTRY.invoke("probability.poisson_cdf", k=k, lam=lam)


class TestNormalPDF:
    def test_normal_pdf_standard_at_0(self) -> None:
        # f(0; 0, 1) = 1/sqrt(2π) ≈ 0.3989422804
        result = Decimal(_npdf("0")["result"])
        expected = Decimal("0.3989422804")
        assert abs(result - expected) < Decimal("1E-8")

    def test_normal_pdf_symmetry(self) -> None:
        # f(-x) = f(x) for standard normal
        r1 = Decimal(_npdf("1.5")["result"])
        r2 = Decimal(_npdf("-1.5")["result"])
        assert abs(r1 - r2) < Decimal("1E-10")

    def test_normal_pdf_non_standard(self) -> None:
        # f(5; 5, 2) = f(0; 0, 1) / 2
        r_std  = Decimal(_npdf("0", sigma="2")["result"])
        r_orig = Decimal(_npdf("5", mu="5", sigma="2")["result"])
        assert abs(r_std - r_orig) < Decimal("1E-10")

    def test_normal_pdf_sigma_zero_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _npdf("0", sigma="0")

    def test_normal_pdf_sigma_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _npdf("0", sigma="-1")

    def test_normal_pdf_invalid_input_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _npdf("abc")

    def test_normal_pdf_trace(self) -> None:
        result = _npdf("0")
        assert result["trace"]["tool"] == "probability.normal_pdf"


class TestNormalCDF:
    def test_normal_cdf_zero(self) -> None:
        # P(X < 0) for standard normal = 0.5
        result = Decimal(_ncdf("0")["result"])
        assert abs(result - Decimal("0.5")) < Decimal("1E-9")

    def test_normal_cdf_large_positive(self) -> None:
        # P(X < 10) ≈ 1
        result = Decimal(_ncdf("10")["result"])
        assert result > Decimal("0.9999")

    def test_normal_cdf_large_negative(self) -> None:
        # P(X < -10) ≈ 0
        result = Decimal(_ncdf("-10")["result"])
        assert result < Decimal("0.0001")

    def test_normal_cdf_95th_percentile(self) -> None:
        # P(X < 1.645) ≈ 0.95 for standard normal
        result = Decimal(_ncdf("1.6448536269514729")["result"])
        assert abs(result - Decimal("0.95")) < Decimal("1E-6")

    def test_normal_cdf_monotone(self) -> None:
        r1 = Decimal(_ncdf("-1")["result"])
        r2 = Decimal(_ncdf("0")["result"])
        r3 = Decimal(_ncdf("1")["result"])
        assert r1 < r2 < r3

    def test_normal_cdf_sigma_zero_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _ncdf("0", sigma="0")

    def test_normal_cdf_trace(self) -> None:
        result = _ncdf("0")
        assert result["trace"]["tool"] == "probability.normal_cdf"


class TestNormalPPF:
    def test_normal_ppf_half(self) -> None:
        # ppf(0.5) = 0 for standard normal
        result = Decimal(_nppf("0.5")["result"])
        assert abs(result - Decimal("0")) < Decimal("1E-9")

    def test_normal_ppf_095(self) -> None:
        # ppf(0.95) ≈ 1.6449
        result = Decimal(_nppf("0.95")["result"])
        assert abs(result - Decimal("1.6449")) < Decimal("0.001")

    def test_normal_ppf_inverse_of_cdf(self) -> None:
        # ppf(cdf(x)) should recover x
        x_str = "1.23"
        cdf_val = _ncdf(x_str)["result"]
        ppf_val = Decimal(_nppf(cdf_val)["result"])
        assert abs(ppf_val - Decimal(x_str)) < Decimal("1E-6")

    def test_normal_ppf_boundary_0_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _nppf("0")

    def test_normal_ppf_boundary_1_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _nppf("1")

    def test_normal_ppf_trace(self) -> None:
        result = _nppf("0.5")
        assert result["trace"]["tool"] == "probability.normal_ppf"


class TestBinomialPMF:
    def test_binomial_pmf_coin_5_10(self) -> None:
        # PMF(k=5, n=10, p=0.5) ≈ 0.2460937500
        result = Decimal(_bpmf(5, 10, "0.5")["result"])
        expected = Decimal("0.2460937500")
        assert abs(result - expected) < Decimal("1E-6")

    def test_binomial_pmf_k_0(self) -> None:
        # P(X=0; n=5, p=0.3) = 0.7^5 ≈ 0.16807
        result = Decimal(_bpmf(0, 5, "0.3")["result"])
        expected = Decimal("0.16807")
        assert abs(result - expected) < Decimal("1E-5")

    def test_binomial_pmf_k_n(self) -> None:
        # P(X=3; n=3, p=0.5) = 0.125
        result = Decimal(_bpmf(3, 3, "0.5")["result"])
        assert abs(result - Decimal("0.125")) < Decimal("1E-9")

    def test_binomial_pmf_k_gt_n_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _bpmf(6, 5, "0.5")

    def test_binomial_pmf_negative_k_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _bpmf(-1, 5, "0.5")

    def test_binomial_pmf_invalid_p_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _bpmf(2, 5, "1.5")

    def test_binomial_pmf_trace(self) -> None:
        result = _bpmf(5, 10, "0.5")
        assert result["trace"]["tool"] == "probability.binomial_pmf"


class TestBinomialCDF:
    def test_binomial_cdf_k_n(self) -> None:
        # P(X <= n) = 1
        result = Decimal(_bcdf(10, 10, "0.5")["result"])
        assert abs(result - Decimal("1")) < Decimal("1E-9")

    def test_binomial_cdf_k_0(self) -> None:
        # P(X <= 0; n=5, p=0.5) = 0.5^5 = 0.03125
        result = Decimal(_bcdf(0, 5, "0.5")["result"])
        assert abs(result - Decimal("0.03125")) < Decimal("1E-9")

    def test_binomial_cdf_monotone(self) -> None:
        r0 = Decimal(_bcdf(0, 10, "0.5")["result"])
        r5 = Decimal(_bcdf(5, 10, "0.5")["result"])
        r9 = Decimal(_bcdf(9, 10, "0.5")["result"])
        assert r0 < r5 < r9

    def test_binomial_cdf_trace(self) -> None:
        result = _bcdf(5, 10, "0.5")
        assert result["trace"]["tool"] == "probability.binomial_cdf"


class TestPoissonPMF:
    def test_poisson_pmf_k0_lam3(self) -> None:
        # P(X=0; λ=3) = e^(-3) ≈ 0.0497870684
        result = Decimal(_ppmf(0, "3")["result"])
        expected = Decimal("0.0497870684")
        assert abs(result - expected) < Decimal("1E-6")

    def test_poisson_pmf_k1_lam1(self) -> None:
        # P(X=1; λ=1) = e^(-1) ≈ 0.3678794412
        result = Decimal(_ppmf(1, "1")["result"])
        expected = Decimal("0.3678794412")
        assert abs(result - expected) < Decimal("1E-6")

    def test_poisson_pmf_lam_zero_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _ppmf(0, "0")

    def test_poisson_pmf_negative_k_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _ppmf(-1, "3")

    def test_poisson_pmf_invalid_lam_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _ppmf(0, "abc")

    def test_poisson_pmf_trace(self) -> None:
        result = _ppmf(0, "3")
        assert result["trace"]["tool"] == "probability.poisson_pmf"


class TestPoissonCDF:
    def test_poisson_cdf_large_k(self) -> None:
        # P(X <= 100; λ=1) ≈ 1
        result = Decimal(_pcdf(100, "1")["result"])
        assert result > Decimal("0.9999")

    def test_poisson_cdf_k0(self) -> None:
        # P(X <= 0; λ=2) = e^(-2) ≈ 0.1353352832
        result = Decimal(_pcdf(0, "2")["result"])
        expected = Decimal("0.1353352832")
        assert abs(result - expected) < Decimal("1E-6")

    def test_poisson_cdf_monotone(self) -> None:
        r0 = Decimal(_pcdf(0, "3")["result"])
        r2 = Decimal(_pcdf(2, "3")["result"])
        r5 = Decimal(_pcdf(5, "3")["result"])
        assert r0 < r2 < r5

    def test_poisson_cdf_trace(self) -> None:
        result = _pcdf(2, "3")
        assert result["trace"]["tool"] == "probability.poisson_cdf"


class TestDistributionsBatchRaceFree:
    def test_probability_batch_race_free(self) -> None:
        expected_cdf = _ncdf("0")["result"]

        def run() -> str:
            return _ncdf("0")["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(50)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == expected_cdf, "Race condition in normal_cdf"
