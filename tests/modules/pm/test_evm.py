"""Tests for PM Earned Value Management (EVM) tool."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.pm  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _evm(pv: str, ev: str, ac: str, bac: str) -> dict:
    return REGISTRY.invoke("pm.evm", pv=pv, ev=ev, ac=ac, bac=bac)


class TestEVMOnTrack:
    def test_evm_on_track(self) -> None:
        """pv=100, ev=100, ac=100, bac=1000 => spi=1, cpi=1, eac=1000, vac=0."""
        r = _evm("100", "100", "100", "1000")
        assert Decimal(r["spi"]) == Decimal("1")
        assert Decimal(r["cpi"]) == Decimal("1")
        assert Decimal(r["sv"])  == Decimal("0")
        assert Decimal(r["cv"])  == Decimal("0")
        assert Decimal(r["eac"]) == Decimal("1000")
        assert Decimal(r["etc_"]) == Decimal("900")
        assert Decimal(r["vac"])  == Decimal("0")

    def test_evm_trace_present(self) -> None:
        r = _evm("100", "100", "100", "1000")
        assert "trace" in r
        assert r["trace"]["tool"] == "pm.evm"


class TestEVMBehindOverBudget:
    def test_evm_behind_over(self) -> None:
        """pv=100, ev=80, ac=120 => behind schedule, over budget."""
        r = _evm("100", "80", "120", "1000")
        spi = Decimal(r["spi"])
        cpi = Decimal(r["cpi"])
        sv  = Decimal(r["sv"])
        cv  = Decimal(r["cv"])

        # SPI = 80/100 = 0.80
        assert abs(spi - Decimal("0.8")) < Decimal("1E-9")
        # CPI = 80/120 = 0.6666...
        assert abs(cpi - Decimal("80") / Decimal("120")) < Decimal("1E-9")
        # SV = 80 - 100 = -20 (behind schedule)
        assert sv == Decimal("-20")
        # CV = 80 - 120 = -40 (over budget)
        assert cv == Decimal("-40")

    def test_evm_ahead_under(self) -> None:
        """ev > pv, ev > ac => ahead of schedule, under budget."""
        r = _evm("80", "100", "90", "1000")
        assert Decimal(r["spi"]) > Decimal("1")
        assert Decimal(r["cpi"]) > Decimal("1")
        assert Decimal(r["sv"]) > Decimal("0")
        assert Decimal(r["cv"]) > Decimal("0")

    def test_evm_eac_formula(self) -> None:
        """EAC = BAC / CPI must hold."""
        r = _evm("100", "80", "120", "2000")
        cpi = Decimal("80") / Decimal("120")
        eac_expected = Decimal("2000") / cpi
        assert abs(Decimal(r["eac"]) - eac_expected) < Decimal("1E-6")

    def test_evm_vac_formula(self) -> None:
        """VAC = BAC - EAC must hold."""
        r = _evm("100", "80", "120", "2000")
        vac_expected = Decimal("2000") - Decimal(r["eac"])
        assert abs(Decimal(r["vac"]) - vac_expected) < Decimal("1E-9")


class TestEVMValidation:
    def test_evm_zero_pv_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _evm("0", "50", "60", "1000")

    def test_evm_zero_ac_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _evm("100", "50", "0", "1000")

    def test_evm_zero_bac_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _evm("100", "50", "60", "0")

    def test_evm_negative_bac_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _evm("100", "50", "60", "-100")

    def test_evm_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _evm("abc", "100", "100", "1000")


class TestEVMBatchRaceFree:
    def test_pm_batch_race_free(self) -> None:
        expected_spi = _evm("100", "100", "100", "1000")["spi"]

        def run() -> str:
            return _evm("100", "100", "100", "1000")["spi"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == expected_spi, f"Race condition: got {r}"
