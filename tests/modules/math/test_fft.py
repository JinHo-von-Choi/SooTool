"""Tests for math.fft and math.ifft."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.math  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestFFT:
    def test_dc_component(self) -> None:
        # Constant signal [3, 3, 3, 3] → X[0] = 12, rest = 0
        r = REGISTRY.invoke("math.fft", samples=["3", "3", "3", "3"])
        assert r["n"] == 4
        assert abs(Decimal(r["bins"][0]["magnitude"]) - Decimal("12")) < Decimal("1E-8")
        for k in range(1, 4):
            assert abs(Decimal(r["bins"][k]["magnitude"])) < Decimal("1E-8")

    def test_fft_ifft_roundtrip(self) -> None:
        samples = ["1", "2", "3", "4"]
        spectrum = REGISTRY.invoke("math.fft", samples=samples)
        inverse  = REGISTRY.invoke("math.ifft", bins=spectrum["bins"], real_output=True)
        for src, got in zip(samples, inverse["samples"], strict=True):
            assert abs(Decimal(got) - Decimal(src)) < Decimal("1E-8")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("math.fft", samples=[])


class TestBatchRaceFree:
    def test_fft_race_free(self) -> None:
        baseline = REGISTRY.invoke("math.fft", samples=["1", "2", "3", "4"])["bins"]

        def run() -> list:
            return REGISTRY.invoke("math.fft", samples=["1", "2", "3", "4"])["bins"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
