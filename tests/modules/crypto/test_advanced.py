"""Tests for crypto advanced tools: egcd, CRT, Euler totient, Carmichael."""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.crypto  # noqa: F401
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY


class TestEGCD:
    def test_gcd_240_46(self) -> None:
        r = REGISTRY.invoke("crypto.egcd", a="240", b="46")
        assert r["gcd"] == "2"
        # Verify Bezout: 240*x + 46*y == 2
        x = int(r["x"])
        y = int(r["y"])
        assert 240 * x + 46 * y == 2

    def test_gcd_17_13_coprime(self) -> None:
        r = REGISTRY.invoke("crypto.egcd", a="17", b="13")
        assert r["gcd"] == "1"
        x = int(r["x"])
        y = int(r["y"])
        assert 17 * x + 13 * y == 1

    def test_gcd_zero_edge(self) -> None:
        r = REGISTRY.invoke("crypto.egcd", a="0", b="5")
        assert r["gcd"] == "5"


class TestCRT:
    def test_classic_example(self) -> None:
        # x ≡ 2 mod 3, 3 mod 5, 2 mod 7 → x ≡ 23 mod 105
        r = REGISTRY.invoke(
            "crypto.crt", residues=["2", "3", "2"], moduli=["3", "5", "7"],
        )
        assert r["x"] == "23"
        assert r["modulus"] == "105"

    def test_non_coprime_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "crypto.crt", residues=["1", "2"], moduli=["4", "6"],
            )

    def test_single_equation(self) -> None:
        r = REGISTRY.invoke(
            "crypto.crt", residues=["5"], moduli=["7"],
        )
        assert r["x"] == "5"
        assert r["modulus"] == "7"


class TestEulerTotient:
    def test_phi_12(self) -> None:
        r = REGISTRY.invoke("crypto.euler_totient", n="12")
        assert r["phi"] == "4"

    def test_phi_prime(self) -> None:
        # phi(13) = 12
        r = REGISTRY.invoke("crypto.euler_totient", n="13")
        assert r["phi"] == "12"

    def test_phi_1(self) -> None:
        r = REGISTRY.invoke("crypto.euler_totient", n="1")
        assert r["phi"] == "1"

    def test_phi_60_known(self) -> None:
        # phi(60) = 60 * (1-1/2) * (1-1/3) * (1-1/5) = 16
        r = REGISTRY.invoke("crypto.euler_totient", n="60")
        assert r["phi"] == "16"


class TestCarmichael:
    def test_lambda_12(self) -> None:
        # λ(12) = lcm(λ(4), λ(3)) = lcm(2, 2) = 2
        r = REGISTRY.invoke("crypto.carmichael_lambda", n="12")
        assert r["lambda"] == "2"

    def test_lambda_15(self) -> None:
        # λ(15) = lcm(λ(3), λ(5)) = lcm(2, 4) = 4
        r = REGISTRY.invoke("crypto.carmichael_lambda", n="15")
        assert r["lambda"] == "4"

    def test_lambda_prime_power(self) -> None:
        # λ(9) = 6 (φ(9)=6)
        r = REGISTRY.invoke("crypto.carmichael_lambda", n="9")
        assert r["lambda"] == "6"


class TestBatchRaceFree:
    def test_egcd_race_free(self) -> None:
        baseline = REGISTRY.invoke("crypto.egcd", a="240", b="46")

        def run() -> dict:
            return REGISTRY.invoke("crypto.egcd", a="240", b="46")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r["gcd"] == baseline["gcd"]
            assert r["x"] == baseline["x"]
            assert r["y"] == baseline["y"]
