"""Tests for crypto.hash tool."""
from __future__ import annotations

import hashlib

import pytest

import sootool.modules.crypto  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _hash(data: str, algorithm: str = "sha256") -> dict:
    return REGISTRY.invoke("crypto.hash", data=data, algorithm=algorithm)


class TestHashSha256:
    # Known SHA-256 value for "hello"
    _HELLO_SHA256 = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_hash_sha256_hello(self) -> None:
        result = _hash("hello", "sha256")
        assert result["hex"] == self._HELLO_SHA256

    def test_hash_sha256_empty(self) -> None:
        expected = hashlib.sha256(b"").hexdigest()
        result = _hash("", "sha256")
        assert result["hex"] == expected

    def test_hash_sha256_length(self) -> None:
        result = _hash("test data", "sha256")
        assert len(result["hex"]) == 64  # 256 bits = 64 hex chars

    def test_hash_sha256_case_insensitive_algo(self) -> None:
        result = _hash("hello", "SHA256")
        assert result["hex"] == self._HELLO_SHA256

    def test_hash_sha256_deterministic(self) -> None:
        r1 = _hash("deterministic test", "sha256")
        r2 = _hash("deterministic test", "sha256")
        assert r1["hex"] == r2["hex"]

    def test_hash_sha256_different_input(self) -> None:
        r1 = _hash("hello", "sha256")
        r2 = _hash("world", "sha256")
        assert r1["hex"] != r2["hex"]

    def test_hash_sha256_unicode(self) -> None:
        data = "안녕하세요"
        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        result = _hash(data, "sha256")
        assert result["hex"] == expected

    def test_hash_sha256_trace_present(self) -> None:
        result = _hash("hello", "sha256")
        assert "trace" in result
        assert result["trace"]["tool"] == "crypto.hash"


class TestHashSha512:
    def test_hash_sha512_hello(self) -> None:
        expected = hashlib.sha512(b"hello").hexdigest()
        result = _hash("hello", "sha512")
        assert result["hex"] == expected

    def test_hash_sha512_length(self) -> None:
        result = _hash("test", "sha512")
        assert len(result["hex"]) == 128  # 512 bits = 128 hex chars

    def test_hash_sha512_empty(self) -> None:
        expected = hashlib.sha512(b"").hexdigest()
        result = _hash("", "sha512")
        assert result["hex"] == expected

    def test_hash_sha512_different_from_sha256(self) -> None:
        r256 = _hash("hello", "sha256")
        r512 = _hash("hello", "sha512")
        assert r256["hex"] != r512["hex"]


class TestHashBlake2b:
    def test_hash_blake2b_hello(self) -> None:
        expected = hashlib.blake2b(b"hello").hexdigest()
        result = _hash("hello", "blake2b")
        assert result["hex"] == expected

    def test_hash_blake2b_empty(self) -> None:
        expected = hashlib.blake2b(b"").hexdigest()
        result = _hash("", "blake2b")
        assert result["hex"] == expected

    def test_hash_blake2b_length(self) -> None:
        result = _hash("test", "blake2b")
        assert len(result["hex"]) == 128  # BLAKE2b default is 64 bytes = 128 hex chars

    def test_hash_blake2b_deterministic(self) -> None:
        r1 = _hash("blake2b test", "blake2b")
        r2 = _hash("blake2b test", "blake2b")
        assert r1["hex"] == r2["hex"]


class TestHashValidation:
    def test_hash_unsupported_algorithm(self) -> None:
        with pytest.raises(InvalidInputError):
            _hash("data", "md5")

    def test_hash_unsupported_algorithm_empty(self) -> None:
        with pytest.raises(InvalidInputError):
            _hash("data", "")

    def test_hash_unsupported_algorithm_sha1(self) -> None:
        with pytest.raises(InvalidInputError):
            _hash("data", "sha1")

    # Property: hash is hex string only
    def test_hash_output_is_hex(self) -> None:
        for algo in ["sha256", "sha512", "blake2b"]:
            result = _hash("test", algo)
            hex_str = result["hex"]
            assert all(c in "0123456789abcdef" for c in hex_str), (
                f"Non-hex char in {algo} output"
            )
