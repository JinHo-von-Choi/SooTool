"""Tests for crypto.is_prime tool (Miller-Rabin primality)."""
from __future__ import annotations

import pytest

import sootool.modules.crypto  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _is_prime(n: str, k: int = 20) -> dict:
    return REGISTRY.invoke("crypto.is_prime", n=n, k=k)


class TestIsPrimeSmall:
    def test_prime_2(self) -> None:
        assert _is_prime("2")["is_prime"] is True

    def test_prime_3(self) -> None:
        assert _is_prime("3")["is_prime"] is True

    def test_prime_5(self) -> None:
        assert _is_prime("5")["is_prime"] is True

    def test_prime_7(self) -> None:
        assert _is_prime("7")["is_prime"] is True

    def test_prime_11(self) -> None:
        assert _is_prime("11")["is_prime"] is True

    def test_prime_13(self) -> None:
        assert _is_prime("13")["is_prime"] is True

    def test_prime_97(self) -> None:
        assert _is_prime("97")["is_prime"] is True

    def test_composite_4(self) -> None:
        assert _is_prime("4")["is_prime"] is False

    def test_composite_9(self) -> None:
        assert _is_prime("9")["is_prime"] is False

    def test_composite_15(self) -> None:
        assert _is_prime("15")["is_prime"] is False

    def test_composite_1(self) -> None:
        assert _is_prime("1")["is_prime"] is False

    def test_composite_0(self) -> None:
        assert _is_prime("0")["is_prime"] is False

    def test_negative(self) -> None:
        assert _is_prime("-7")["is_prime"] is False

    def test_composite_100(self) -> None:
        assert _is_prime("100")["is_prime"] is False

    def test_composite_1000(self) -> None:
        assert _is_prime("1000")["is_prime"] is False


class TestIsPrimeLarge:
    def test_mersenne_prime_61(self) -> None:
        # 2^61 - 1 = 2305843009213693951 is a Mersenne prime
        result = _is_prime(str(2**61 - 1))
        assert result["is_prime"] is True

    def test_mersenne_prime_31(self) -> None:
        # 2^31 - 1 = 2147483647 is prime
        result = _is_prime(str(2**31 - 1))
        assert result["is_prime"] is True

    def test_large_composite(self) -> None:
        # 2^61 is obviously composite (even)
        result = _is_prime(str(2**61))
        assert result["is_prime"] is False

    def test_known_large_prime(self) -> None:
        # 10^9 + 7 is a well-known prime
        result = _is_prime("1000000007")
        assert result["is_prime"] is True

    def test_known_large_composite(self) -> None:
        # 10^9 + 8 is even, hence composite
        result = _is_prime("1000000008")
        assert result["is_prime"] is False

    def test_prime_above_4_billion(self) -> None:
        # 4294967311 is prime (> 2^32)
        result = _is_prime("4294967311")
        assert result["is_prime"] is True

    def test_carmichael_number(self) -> None:
        # 561 = 3*11*17 is the smallest Carmichael number (composite)
        # Fermat test would wrongly say prime; Miller-Rabin correctly says composite
        result = _is_prime("561")
        assert result["is_prime"] is False

    def test_trace_present(self) -> None:
        result = _is_prime("7")
        assert "trace" in result
        assert result["trace"]["tool"] == "crypto.is_prime"


class TestIsPrimeKnownList:
    """Exhaustive check against first 25 primes."""
    _PRIMES = [
        2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
        31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
        73, 79, 83, 89, 97,
    ]
    _COMPOSITES = [4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 22, 24, 25]

    def test_all_small_primes(self) -> None:
        for p in self._PRIMES:
            assert _is_prime(str(p))["is_prime"] is True, f"{p} should be prime"

    def test_all_small_composites(self) -> None:
        for c in self._COMPOSITES:
            assert _is_prime(str(c))["is_prime"] is False, f"{c} should be composite"


class TestIsPrimeValidation:
    def test_invalid_input_string(self) -> None:
        with pytest.raises(InvalidInputError):
            _is_prime("not_a_number")

    def test_invalid_k_zero(self) -> None:
        with pytest.raises(InvalidInputError):
            _is_prime("7", k=0)

    def test_invalid_k_negative(self) -> None:
        with pytest.raises(InvalidInputError):
            _is_prime("7", k=-1)
