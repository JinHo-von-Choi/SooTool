"""Tests for probability expected_value tool."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.probability  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _ev(values: list[str], probs: list[str]) -> dict:
    return REGISTRY.invoke("probability.expected_value", values=values, probabilities=probs)


class TestExpectedValue:
    def test_expected_value_dice(self) -> None:
        # Fair 6-sided die: E = (1+2+3+4+5+6)/6 = 3.5
        # Use exact Decimal fractions (5 equal slices + remainder for exact sum=1)
        p = str(Decimal("1") / Decimal("6"))
        last_p = str(Decimal("1") - Decimal(p) * 5)
        values = ["1", "2", "3", "4", "5", "6"]
        probs  = [p, p, p, p, p, last_p]
        result = Decimal(_ev(values, probs)["result"])
        assert abs(result - Decimal("3.5")) < Decimal("1E-9")

    def test_expected_value_coin(self) -> None:
        # Fair coin: heads=1, tails=0 => E = 0.5
        result = Decimal(_ev(["0", "1"], ["0.5", "0.5"])["result"])
        assert abs(result - Decimal("0.5")) < Decimal("1E-9")

    def test_expected_value_certain_outcome(self) -> None:
        # Only one outcome with prob=1
        result = Decimal(_ev(["42"], ["1"])["result"])
        assert result == Decimal("42")

    def test_expected_value_negative_values(self) -> None:
        # E[-1, 1] with equal probs = 0
        result = Decimal(_ev(["-1", "1"], ["0.5", "0.5"])["result"])
        assert abs(result - Decimal("0")) < Decimal("1E-9")

    def test_expected_value_bad_probs_raises(self) -> None:
        # Probabilities don't sum to 1
        with pytest.raises(DomainConstraintError):
            _ev(["1", "2", "3"], ["0.3", "0.3", "0.3"])

    def test_expected_value_prob_out_of_range_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _ev(["1", "2"], ["1.5", "-0.5"])

    def test_expected_value_length_mismatch_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _ev(["1", "2", "3"], ["0.5", "0.5"])

    def test_expected_value_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _ev([], [])

    def test_expected_value_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _ev(["abc"], ["1"])

    def test_expected_value_trace(self) -> None:
        result = _ev(["1", "2"], ["0.5", "0.5"])
        assert "trace" in result
        assert result["trace"]["tool"] == "probability.expected_value"

    def test_expected_value_weighted(self) -> None:
        # Non-uniform distribution: values [0, 1, 2] with probs [0.25, 0.50, 0.25]
        # E = 0*0.25 + 1*0.50 + 2*0.25 = 1.0
        result = Decimal(_ev(["0", "1", "2"], ["0.25", "0.50", "0.25"])["result"])
        assert abs(result - Decimal("1.0")) < Decimal("1E-9")


class TestExpectedValueBatchRaceFree:
    def test_probability_batch_race_free(self) -> None:
        # Use exact probabilities that avoid Decimal division ambiguity
        values = ["0", "1", "2"]
        probs  = ["0.25", "0.50", "0.25"]
        # E = 0*0.25 + 1*0.50 + 2*0.25 = 1.0  (exact)
        expected_val = Decimal("1")

        def run() -> Decimal:
            return Decimal(_ev(values, probs)["result"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert abs(r - expected_val) < Decimal("1E-9"), f"Race condition: got {r}"
