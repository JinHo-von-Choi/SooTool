"""Tests for probability Bayes theorem tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.probability  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _bayes(prior: str, likelihood: str, marginal: str) -> dict:
    return REGISTRY.invoke(
        "probability.bayes",
        prior=prior,
        likelihood=likelihood,
        marginal=marginal,
    )


class TestBayes:
    def test_bayes_medical_test(self) -> None:
        """Classic cancer screening example.

        Disease prevalence (prior): 0.01
        Test sensitivity (likelihood P(+|disease)): 0.9
        P(+) (marginal): P(+|disease)*P(disease) + P(+|no disease)*P(no disease)
                       = 0.9*0.01 + 0.1*0.99 = 0.009 + 0.099 = 0.108

        Posterior P(disease|+) = 0.01 * 0.9 / 0.108 = 0.009 / 0.108 ≈ 0.08333...
        """
        result = _bayes(prior="0.01", likelihood="0.9", marginal="0.108")
        posterior = Decimal(result["posterior"])
        expected  = Decimal("0.009") / Decimal("0.108")
        assert abs(posterior - expected) < Decimal("1E-10")

    def test_bayes_certain_prior(self) -> None:
        """If prior = 1, posterior = likelihood / marginal."""
        result = _bayes(prior="1", likelihood="0.8", marginal="0.8")
        assert Decimal(result["posterior"]) == Decimal("1")

    def test_bayes_zero_prior(self) -> None:
        """If prior = 0, posterior must be 0."""
        result = _bayes(prior="0", likelihood="0.9", marginal="0.5")
        assert Decimal(result["posterior"]) == Decimal("0")

    def test_bayes_fifty_fifty(self) -> None:
        """Equal prior/marginal => posterior = likelihood."""
        result = _bayes(prior="0.5", likelihood="0.6", marginal="0.3")
        posterior = Decimal(result["posterior"])
        expected  = Decimal("0.5") * Decimal("0.6") / Decimal("0.3")
        assert abs(posterior - expected) < Decimal("1E-10")

    def test_bayes_prior_out_of_range_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _bayes(prior="1.1", likelihood="0.5", marginal="0.5")

    def test_bayes_likelihood_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _bayes(prior="0.5", likelihood="-0.1", marginal="0.5")

    def test_bayes_zero_marginal_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _bayes(prior="0.5", likelihood="0.8", marginal="0")

    def test_bayes_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _bayes(prior="abc", likelihood="0.5", marginal="0.5")

    def test_bayes_trace_present(self) -> None:
        result = _bayes(prior="0.3", likelihood="0.7", marginal="0.5")
        assert "trace" in result
        assert result["trace"]["tool"] == "probability.bayes"

    def test_bayes_symmetry_check(self) -> None:
        """P(A|B) and P(B|A) are related but generally not equal."""
        r1 = _bayes(prior="0.3", likelihood="0.6", marginal="0.4")
        r2 = _bayes(prior="0.4", likelihood=str(Decimal(r1["posterior"])), marginal="0.6")
        # r2 should recover 0.3 (original prior)
        assert abs(Decimal(r2["posterior"]) - Decimal("0.3")) < Decimal("1E-8")
