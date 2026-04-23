"""Tests for science electrochemistry tools: Nernst, Faraday, battery capacity."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.science  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestNernst:
    def test_q_1_equals_e0(self) -> None:
        # ln(1) = 0 → E = E0
        r = REGISTRY.invoke("science.nernst", e0="1.5", n=2, reaction_q="1")
        assert Decimal(r["e"]).quantize(Decimal("0.000001")) == Decimal("1.500000")

    def test_q_greater_than_1_e_less(self) -> None:
        # Q > 1 → E < E0
        r = REGISTRY.invoke("science.nernst", e0="0.8", n=1, reaction_q="10")
        assert Decimal(r["e"]) < Decimal("0.8")

    def test_q_zero_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("science.nernst", e0="0.8", n=1, reaction_q="0")


class TestFaraday:
    def test_copper_deposition(self) -> None:
        # Cu²⁺ + 2e⁻ → Cu; I=1A, t=3600s, M=63.546 g/mol, n=2
        r = REGISTRY.invoke(
            "science.faraday_electrolysis",
            current_a="1", time_s="3600", molar_mass_g="63.546", n_electrons=2,
        )
        # expected ~ 1.1858 g
        assert abs(Decimal(r["mass_g"]) - Decimal("1.1858")) < Decimal("0.01")

    def test_n_zero_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "science.faraday_electrolysis",
                current_a="1", time_s="3600", molar_mass_g="63.5", n_electrons=0,
            )


class TestBattery:
    def test_ah_to_wh(self) -> None:
        r = REGISTRY.invoke(
            "science.battery_capacity", value="10", voltage="12", mode="ah_to_wh",
        )
        assert Decimal(r["result"]) == Decimal("120")
        assert r["unit"] == "Wh"

    def test_wh_to_ah(self) -> None:
        r = REGISTRY.invoke(
            "science.battery_capacity", value="120", voltage="12", mode="wh_to_ah",
        )
        assert Decimal(r["result"]) == Decimal("10")
        assert r["unit"] == "Ah"

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "science.battery_capacity", value="10", voltage="12", mode="foo",
            )


class TestBatchRaceFree:
    def test_nernst_race_free(self) -> None:
        baseline = REGISTRY.invoke("science.nernst", e0="0.5", n=2, reaction_q="2")["e"]

        def run() -> str:
            return REGISTRY.invoke("science.nernst", e0="0.5", n=2, reaction_q="2")["e"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
