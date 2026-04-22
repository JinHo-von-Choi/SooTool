"""Tests for science thermodynamics tool: ideal_gas."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.science  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_R = Decimal("8.314462618")


def _ig(**kwargs) -> dict:
    return REGISTRY.invoke("science.ideal_gas", **kwargs)


class TestIdealGas:
    def test_ideal_gas_stp_moles(self) -> None:
        """At STP-ish (P=101325 Pa, T=273.15 K), 22.4L should be ~1 mol."""
        r = _ig(pressure="101325", volume="0.0224", temperature="273.15")
        n = Decimal(r["moles"])
        # PV / (RT) = 101325 * 0.0224 / (8.314462618 * 273.15) ≈ 0.998 mol
        expected = Decimal("101325") * Decimal("0.0224") / (_R * Decimal("273.15"))
        assert abs(n - expected) < Decimal("0.01")

    def test_ideal_gas_compute_pressure(self) -> None:
        """Compute P from V, n, T."""
        r = _ig(volume="0.001", moles="1", temperature="300")
        P = Decimal(r["pressure"])
        expected = Decimal("1") * _R * Decimal("300") / Decimal("0.001")
        assert abs(P - expected) < Decimal("0.001")

    def test_ideal_gas_compute_volume(self) -> None:
        """Compute V from P, n, T."""
        r = _ig(pressure="101325", moles="1", temperature="273.15")
        V = Decimal(r["volume"])
        expected = Decimal("1") * _R * Decimal("273.15") / Decimal("101325")
        assert abs(V - expected) < Decimal("0.00001")

    def test_ideal_gas_compute_temperature(self) -> None:
        """Compute T from P, V, n."""
        r = _ig(pressure="101325", volume="0.0224143", moles="1")
        T = Decimal(r["temperature"])
        expected = Decimal("101325") * Decimal("0.0224143") / (_R * Decimal("1"))
        assert abs(T - expected) < Decimal("0.01")

    def test_ideal_gas_compute_moles(self) -> None:
        """Compute n from P, V, T."""
        r = _ig(pressure="101325", volume="0.02271", temperature="273.15")
        n = Decimal(r["moles"])
        expected = Decimal("101325") * Decimal("0.02271") / (_R * Decimal("273.15"))
        assert abs(n - expected) < Decimal("0.0001")

    def test_ideal_gas_pv_equals_nrt(self) -> None:
        """Verify PV = nRT for computed value."""
        r = _ig(pressure="200000", moles="2", temperature="350")
        V = Decimal(r["volume"])
        lhs = Decimal("200000") * V
        rhs = Decimal("2") * _R * Decimal("350")
        assert abs(lhs - rhs) < Decimal("0.001")

    def test_ideal_gas_two_unknowns_raises(self) -> None:
        """Providing only 2 variables must raise DomainConstraintError."""
        with pytest.raises(DomainConstraintError):
            _ig(pressure="101325", volume="0.022")

    def test_ideal_gas_four_given_raises(self) -> None:
        """Providing all 4 variables must raise DomainConstraintError."""
        with pytest.raises(DomainConstraintError):
            _ig(pressure="101325", volume="0.022", moles="1", temperature="273")

    def test_ideal_gas_zero_volume_for_pressure_raises(self) -> None:
        """If computing P and V=0, should raise DomainConstraintError."""
        with pytest.raises(DomainConstraintError):
            _ig(volume="0", moles="1", temperature="300")

    def test_ideal_gas_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _ig(pressure="abc", volume="0.022", moles="1")

    def test_ideal_gas_trace(self) -> None:
        r = _ig(pressure="101325", volume="0.0224", temperature="273.15")
        assert "trace" in r
        assert r["trace"]["tool"] == "science.ideal_gas"


class TestIdealGasBatchRaceFree:
    def test_science_batch_race_free(self) -> None:
        # Use exact-representable inputs to ensure deterministic Decimal output
        # P=100000, V=1, T=1000 => n = PV/(RT) = 100000/(8.314462618*1000)
        expected = Decimal(
            _ig(pressure="100000", volume="1", temperature="1000")["moles"]
        )

        def run() -> Decimal:
            return Decimal(
                _ig(pressure="100000", volume="1", temperature="1000")["moles"]
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert abs(r - expected) < Decimal("1E-20"), f"Race condition in ideal_gas: {r}"
