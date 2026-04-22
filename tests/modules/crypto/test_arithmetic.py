"""Tests for crypto.gcd, crypto.lcm, crypto.modpow, crypto.modinv."""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.crypto  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _gcd(a: str, b: str) -> dict:
    return REGISTRY.invoke("crypto.gcd", a=a, b=b)


def _lcm(a: str, b: str) -> dict:
    return REGISTRY.invoke("crypto.lcm", a=a, b=b)


def _modpow(base: str, exponent: str, modulus: str) -> dict:
    return REGISTRY.invoke("crypto.modpow", base=base, exponent=exponent, modulus=modulus)


def _modinv(a: str, m: str) -> dict:
    return REGISTRY.invoke("crypto.modinv", a=a, m=m)


class TestGcd:
    def test_gcd_48_18(self) -> None:
        result = _gcd("48", "18")
        assert result["result"] == "6"

    def test_gcd_100_75(self) -> None:
        result = _gcd("100", "75")
        assert result["result"] == "25"

    def test_gcd_prime_coprime(self) -> None:
        # gcd(13, 7) = 1
        result = _gcd("13", "7")
        assert result["result"] == "1"

    def test_gcd_same_number(self) -> None:
        result = _gcd("42", "42")
        assert result["result"] == "42"

    def test_gcd_zero_a(self) -> None:
        # gcd(0, n) = n
        result = _gcd("0", "15")
        assert result["result"] == "15"

    def test_gcd_zero_both(self) -> None:
        result = _gcd("0", "0")
        assert result["result"] == "0"

    def test_gcd_negative_inputs(self) -> None:
        # gcd treats negative as absolute
        result = _gcd("-48", "18")
        assert result["result"] == "6"

    def test_gcd_large(self) -> None:
        result = _gcd("123456789012345678", "987654321098765432")
        assert int(result["result"]) > 0  # sanity

    def test_gcd_trace_present(self) -> None:
        result = _gcd("12", "8")
        assert "trace" in result
        assert result["trace"]["tool"] == "crypto.gcd"

    def test_gcd_invalid_input(self) -> None:
        with pytest.raises(InvalidInputError):
            _gcd("abc", "5")

    # Property-based style: gcd(a,b) divides both a and b
    def test_gcd_divides_both(self) -> None:
        for a, b in [(36, 60), (100, 250), (7, 49), (17, 51)]:
            result = _gcd(str(a), str(b))
            g = int(result["result"])
            assert a % g == 0
            assert b % g == 0

    # Property: gcd(a,b) == gcd(b,a)
    def test_gcd_commutative(self) -> None:
        pairs = [("48", "18"), ("100", "75"), ("1000", "123")]
        for a, b in pairs:
            assert _gcd(a, b)["result"] == _gcd(b, a)["result"]


class TestLcm:
    def test_lcm_48_18(self) -> None:
        result = _lcm("48", "18")
        assert result["result"] == "144"

    def test_lcm_4_6(self) -> None:
        result = _lcm("4", "6")
        assert result["result"] == "12"

    def test_lcm_prime_coprime(self) -> None:
        # lcm(7,13) = 91
        result = _lcm("7", "13")
        assert result["result"] == "91"

    def test_lcm_same_number(self) -> None:
        result = _lcm("42", "42")
        assert result["result"] == "42"

    def test_lcm_zero(self) -> None:
        result = _lcm("0", "15")
        assert result["result"] == "0"

    def test_lcm_trace_present(self) -> None:
        result = _lcm("12", "8")
        assert "trace" in result
        assert result["trace"]["tool"] == "crypto.lcm"

    # Property: lcm is multiple of both inputs
    def test_lcm_multiple_of_both(self) -> None:
        for a, b in [(4, 6), (12, 18), (7, 13)]:
            result = _lcm(str(a), str(b))
            lcm_val = int(result["result"])
            assert lcm_val % a == 0
            assert lcm_val % b == 0

    # Property: gcd(a,b) * lcm(a,b) == |a*b|
    def test_lcm_gcd_relation(self) -> None:
        for a, b in [(48, 18), (15, 25), (7, 13)]:
            g       = int(_gcd(str(a), str(b))["result"])
            lcm_val = int(_lcm(str(a), str(b))["result"])
            assert g * lcm_val == a * b


class TestModpow:
    def test_modpow_2_10_1000(self) -> None:
        result = _modpow("2", "10", "1000")
        assert result["result"] == "24"

    def test_modpow_fermat_little(self) -> None:
        # By Fermat's little theorem: a^(p-1) ≡ 1 (mod p) for prime p and gcd(a,p)=1
        # 3^(11-1) mod 11 = 3^10 mod 11 = 1
        result = _modpow("3", "10", "11")
        assert result["result"] == "1"

    def test_modpow_zero_exponent(self) -> None:
        # base^0 mod m = 1 (for m > 1)
        result = _modpow("999", "0", "7")
        assert result["result"] == "1"

    def test_modpow_base_larger_than_modulus(self) -> None:
        result = _modpow("100", "3", "13")
        assert result["result"] == str(pow(100, 3, 13))

    def test_modpow_large_numbers(self) -> None:
        # RSA-like: pow(m, e, n) where m=2, e=65537, n=large prime
        n = str(2**31 - 1)  # Mersenne prime
        result = _modpow("2", "65537", n)
        expected = str(pow(2, 65537, 2**31 - 1))
        assert result["result"] == expected

    def test_modpow_trace_present(self) -> None:
        result = _modpow("2", "10", "1000")
        assert "trace" in result
        assert result["trace"]["tool"] == "crypto.modpow"

    def test_modpow_invalid_modulus_zero(self) -> None:
        with pytest.raises(DomainConstraintError):
            _modpow("2", "10", "0")

    def test_modpow_invalid_modulus_negative(self) -> None:
        with pytest.raises(DomainConstraintError):
            _modpow("2", "10", "-5")

    def test_modpow_invalid_exponent_negative(self) -> None:
        with pytest.raises(DomainConstraintError):
            _modpow("2", "-1", "7")

    def test_modpow_invalid_input(self) -> None:
        with pytest.raises(InvalidInputError):
            _modpow("2", "xyz", "7")

    def test_crypto_batch_race_free(self) -> None:
        """100 parallel modpow calls must return identical results."""
        def call(_: int) -> str:
            return _modpow("2", "100", "1000000007")["result"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            results = list(ex.map(call, range(100)))

        expected = str(pow(2, 100, 1000000007))
        assert all(r == expected for r in results), "Race condition detected"


class TestModinv:
    def test_modinv_3_11(self) -> None:
        # 3*4 = 12 ≡ 1 (mod 11)
        result = _modinv("3", "11")
        assert result["result"] == "4"

    def test_modinv_verification(self) -> None:
        # Verify that a * modinv(a, m) ≡ 1 (mod m) for several pairs
        pairs = [("3", "11"), ("7", "13"), ("5", "17"), ("2", "15")]
        for a, m in pairs:
            result = _modinv(a, m)
            inv = int(result["result"])
            assert (int(a) * inv) % int(m) == 1

    def test_modinv_large(self) -> None:
        # modinv(65537, 10^9 + 7) — 10^9 + 7 is prime so gcd is 1
        a = "65537"
        m = "1000000007"
        result = _modinv(a, m)
        inv = int(result["result"])
        assert (65537 * inv) % 1000000007 == 1

    def test_modinv_trace_present(self) -> None:
        result = _modinv("3", "11")
        assert "trace" in result
        assert result["trace"]["tool"] == "crypto.modinv"

    def test_modinv_not_coprime_raises(self) -> None:
        # gcd(6, 9) = 3 != 1 → no inverse
        with pytest.raises(DomainConstraintError, match="gcd"):
            _modinv("6", "9")

    def test_modinv_gcd2_raises(self) -> None:
        # gcd(4, 6) = 2 != 1
        with pytest.raises(DomainConstraintError):
            _modinv("4", "6")

    def test_modinv_m_equals_1_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _modinv("5", "1")

    def test_modinv_invalid_input(self) -> None:
        with pytest.raises(InvalidInputError):
            _modinv("abc", "11")
