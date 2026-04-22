"""Tests for probability combinatorics tools: factorial, nCr, nPr."""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.probability  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _factorial(n: int) -> dict:
    return REGISTRY.invoke("probability.factorial", n=n)


def _ncr(n: int, r: int) -> dict:
    return REGISTRY.invoke("probability.nCr", n=n, r=r)


def _npr(n: int, r: int) -> dict:
    return REGISTRY.invoke("probability.nPr", n=n, r=r)


class TestFactorial:
    def test_factorial_0(self) -> None:
        assert _factorial(0)["result"] == "1"

    def test_factorial_1(self) -> None:
        assert _factorial(1)["result"] == "1"

    def test_factorial_10(self) -> None:
        assert _factorial(10)["result"] == "3628800"

    def test_factorial_5(self) -> None:
        assert _factorial(5)["result"] == "120"

    def test_factorial_large(self) -> None:
        # 20! = 2432902008176640000
        assert _factorial(20)["result"] == "2432902008176640000"

    def test_factorial_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _factorial(-1)

    def test_factorial_float_raises(self) -> None:
        with pytest.raises((InvalidInputError, TypeError, Exception)):
            _factorial(3.5)  # type: ignore[arg-type]

    def test_factorial_trace_present(self) -> None:
        result = _factorial(5)
        assert "trace" in result
        assert result["trace"]["tool"] == "probability.factorial"

    def test_factorial_very_large(self) -> None:
        # 1000! should produce a large number without error
        result = _factorial(1000)
        assert len(result["result"]) > 100  # definitely a big number


class TestNCr:
    def test_ncr_52_5(self) -> None:
        assert _ncr(52, 5)["result"] == "2598960"

    def test_ncr_10_3(self) -> None:
        assert _ncr(10, 3)["result"] == "120"

    def test_ncr_n_0(self) -> None:
        # C(n, 0) = 1 for any n
        assert _ncr(10, 0)["result"] == "1"

    def test_ncr_n_n(self) -> None:
        # C(n, n) = 1
        assert _ncr(7, 7)["result"] == "1"

    def test_ncr_0_0(self) -> None:
        assert _ncr(0, 0)["result"] == "1"

    def test_ncr_r_gt_n_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _ncr(3, 5)

    def test_ncr_negative_n_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _ncr(-1, 0)

    def test_ncr_trace(self) -> None:
        result = _ncr(5, 2)
        assert "trace" in result
        assert result["trace"]["tool"] == "probability.nCr"


class TestNPr:
    def test_npr_5_3(self) -> None:
        assert _npr(5, 3)["result"] == "60"

    def test_npr_10_2(self) -> None:
        # P(10, 2) = 10*9 = 90
        assert _npr(10, 2)["result"] == "90"

    def test_npr_n_0(self) -> None:
        # P(n, 0) = 1
        assert _npr(6, 0)["result"] == "1"

    def test_npr_n_n(self) -> None:
        # P(n, n) = n!
        assert _npr(4, 4)["result"] == "24"

    def test_npr_r_gt_n_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _npr(3, 5)

    def test_npr_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _npr(-2, 0)

    def test_npr_trace(self) -> None:
        result = _npr(5, 3)
        assert "trace" in result
        assert result["trace"]["tool"] == "probability.nPr"


class TestCombinatoricsBatchRaceFree:
    """Verify thread safety — concurrent calls must not corrupt each other."""

    def test_probability_batch_race_free(self) -> None:
        inputs = [(52, 5), (10, 3), (6, 2), (8, 4), (12, 6)]
        expected = {(n, r): _ncr(n, r)["result"] for n, r in inputs}

        def run(n: int, r: int) -> tuple[int, int, str]:
            return n, r, _ncr(n, r)["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run, n, r) for _ in range(20) for n, r in inputs]
            results = [f.result() for f in futures]

        for n, r, result in results:
            assert result == expected[(n, r)], f"Race condition detected for nCr({n},{r})"
