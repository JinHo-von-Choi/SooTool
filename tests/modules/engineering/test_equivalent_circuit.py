"""Tests for engineering.equivalent_circuit tools (Tier 3)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestTheveninEquivalent:
    def test_basic(self) -> None:
        """V_oc=10, I_sc=0.5 → V_th=10, R_th=20."""
        r = REGISTRY.invoke(
            "engineering.thevenin_equivalent",
            open_circuit_voltage="10", short_circuit_current="0.5",
        )
        assert Decimal(r["v_th"]) == Decimal("10")
        assert Decimal(r["r_th"]) == Decimal("20")

    def test_zero_voltage(self) -> None:
        r = REGISTRY.invoke(
            "engineering.thevenin_equivalent",
            open_circuit_voltage="0", short_circuit_current="1",
        )
        assert Decimal(r["v_th"]) == Decimal("0")
        assert Decimal(r["r_th"]) == Decimal("0")

    def test_zero_isc_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.thevenin_equivalent",
                open_circuit_voltage="10", short_circuit_current="0",
            )

    def test_negative_isc_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.thevenin_equivalent",
                open_circuit_voltage="10", short_circuit_current="-0.5",
            )


class TestNortonEquivalent:
    def test_basic(self) -> None:
        """V_th=12, R_th=4 → I_N=3, R_N=4."""
        r = REGISTRY.invoke(
            "engineering.norton_equivalent",
            v_th="12", r_th="4",
        )
        assert Decimal(r["i_n"]) == Decimal("3")
        assert Decimal(r["r_n"]) == Decimal("4")

    def test_roundtrip_with_thevenin(self) -> None:
        """Thevenin → Norton → 동일 회로 확인."""
        th = REGISTRY.invoke(
            "engineering.thevenin_equivalent",
            open_circuit_voltage="24", short_circuit_current="2",
        )
        nt = REGISTRY.invoke(
            "engineering.norton_equivalent",
            v_th=th["v_th"], r_th=th["r_th"],
        )
        # I_N · R_N should equal V_th
        _assert_close(
            str(Decimal(nt["i_n"]) * Decimal(nt["r_n"])),
            Decimal("24"),
            tol=Decimal("1E-15"),
        )

    def test_zero_r_th_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.norton_equivalent",
                v_th="12", r_th="0",
            )


class TestMaxPowerTransfer:
    def test_basic(self) -> None:
        """V_th=12, R_th=4 → R_L=4, P_max = 144/16 = 9 W."""
        r = REGISTRY.invoke(
            "engineering.max_power_transfer",
            v_th="12", r_th="4",
        )
        assert Decimal(r["optimal_load"]) == Decimal("4")
        assert Decimal(r["max_power"]) == Decimal("9")

    def test_high_voltage(self) -> None:
        r = REGISTRY.invoke(
            "engineering.max_power_transfer",
            v_th="100", r_th="50",
        )
        # P = 10000/200 = 50 W
        assert Decimal(r["max_power"]) == Decimal("50")

    def test_negative_voltage_yields_same_power(self) -> None:
        """V² is sign-insensitive, so P_max 동일."""
        r = REGISTRY.invoke(
            "engineering.max_power_transfer",
            v_th="-12", r_th="4",
        )
        assert Decimal(r["max_power"]) == Decimal("9")

    def test_zero_r_th_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.max_power_transfer",
                v_th="12", r_th="0",
            )


class TestConcurrency:
    def test_max_power_batch_race_free(self) -> None:
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.max_power_transfer",
                v_th=str(n), r_th="0.25",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        # P_max = V² / (4·0.25) = V²
        for n, res in enumerate(results, start=1):
            assert Decimal(res["max_power"]) == Decimal(n * n), f"mismatch at n={n}"
