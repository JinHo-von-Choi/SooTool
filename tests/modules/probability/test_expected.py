"""Tests for probability expected_value tool."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.probability  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.probability.expected import expected_value


def _ev(values: list[str], probs: list[str]) -> dict:
    return REGISTRY.invoke("probability.expected_value", values=values, probabilities=probs)


class TestExpectedValue:
    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "abc"])
    @pytest.mark.parametrize("field", ["values", "probabilities"])
    def test_invalid_number_rejected(self, value: str, field: str) -> None:
        inputs = {"values": ["42"], "probabilities": ["1"]}
        inputs[field] = [value]
        with pytest.raises(InvalidInputError, match=rf"{field}\[0\]"):
            expected_value(**inputs)

    def test_zero_and_one_probability_boundaries(self) -> None:
        result = _ev(["-999", "0.123456789012345678901234567890123456789"], ["0", "1"])
        assert Decimal(result["result"]) == Decimal("0.123456789012345678901234567890123456789")

    @pytest.mark.parametrize("probability", ["0.499999999", "0.500000001"])
    def test_probability_sum_at_tolerance(self, probability: str) -> None:
        result = _ev(["0", "2"], ["0.5", probability])
        assert Decimal(result["result"]) == Decimal(probability) * 2

    @pytest.mark.parametrize("probability", ["0.49999999899999999999", "0.50000000100000000001"])
    def test_probability_sum_just_outside_tolerance(self, probability: str) -> None:
        with pytest.raises(DomainConstraintError):
            _ev(["0", "2"], ["0.5", probability])

    def test_high_precision_weighted_value(self) -> None:
        result = _ev(
            ["0.123456789012345678901234567890", "0.987654321098765432109876543210"],
            ["0.25", "0.75"],
        )
        assert Decimal(result["result"]) == Decimal("0.771604938077160493807716049380")

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
