"""Tests for science physics tool: half_life."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.science  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _hl(initial: str, hl: str, elapsed: str) -> dict:
    return REGISTRY.invoke(
        "science.half_life",
        initial_amount=initial,
        half_life=hl,
        elapsed_time=elapsed,
    )


class TestHalfLife:
    def test_half_life_one_period(self) -> None:
        """t = T: remaining = initial * 0.5 = 50%."""
        r = _hl("100", "10", "10")
        remaining = Decimal(r["remaining"])
        fraction  = Decimal(r["fraction"])
        assert abs(remaining - Decimal("50")) < Decimal("1E-10")
        assert abs(fraction - Decimal("0.5")) < Decimal("1E-10")

    def test_half_life_two_periods(self) -> None:
        """t = 2T: remaining = initial * 0.25 = 25%."""
        r = _hl("200", "5", "10")
        remaining = Decimal(r["remaining"])
        assert abs(remaining - Decimal("50")) < Decimal("1E-10")
        fraction  = Decimal(r["fraction"])
        assert abs(fraction - Decimal("0.25")) < Decimal("1E-10")

    def test_half_life_zero_elapsed(self) -> None:
        """t = 0: all initial remains."""
        r = _hl("500", "10", "0")
        remaining = Decimal(r["remaining"])
        assert abs(remaining - Decimal("500")) < Decimal("1E-10")
        assert abs(Decimal(r["fraction"]) - Decimal("1")) < Decimal("1E-10")

    def test_half_life_fraction_consistency(self) -> None:
        """remaining == initial * fraction."""
        r = _hl("1000", "7", "21")  # t = 3T: fraction = 0.125
        fraction  = Decimal(r["fraction"])
        remaining = Decimal(r["remaining"])
        assert abs(fraction - Decimal("0.125")) < Decimal("1E-10")
        assert abs(remaining - Decimal("125")) < Decimal("1E-8")

    def test_half_life_large_elapsed(self) -> None:
        """Very large t/T ratio gives negligible remaining."""
        r = _hl("1E+15", "1", "100")  # 100 half-lives
        remaining = Decimal(r["remaining"])
        # (0.5)^100 ≈ 7.89e-31 => remaining ≈ 7.89e-16
        assert remaining < Decimal("1E-10")

    def test_half_life_negative_initial_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _hl("-100", "10", "5")

    def test_half_life_zero_initial_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _hl("0", "10", "5")

    def test_half_life_zero_half_life_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _hl("100", "0", "5")

    def test_half_life_negative_elapsed_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _hl("100", "10", "-1")

    def test_half_life_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _hl("abc", "10", "5")

    def test_half_life_trace(self) -> None:
        r = _hl("100", "10", "10")
        assert "trace" in r
        assert r["trace"]["tool"] == "science.half_life"


class TestHalfLifeBatchRaceFree:
    def test_science_batch_race_free(self) -> None:
        expected = _hl("100", "10", "10")["remaining"]

        def run() -> str:
            return _hl("100", "10", "10")["remaining"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == expected, f"Race condition in half_life"
