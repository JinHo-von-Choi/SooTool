"""Tests for QT correction formulas: Bazett, Fridericia, Framingham, Hodges."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.medical  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestBazett:
    def test_qt_400_rr_1000(self) -> None:
        # QTc_B = 400/sqrt(1) = 400 ms
        r = REGISTRY.invoke("medical.qtc_bazett", qt="400", rr="1000", unit="ms")
        assert abs(Decimal(r["qtc"]) - Decimal("400")) < Decimal("1E-6")

    def test_qt_400_rr_800(self) -> None:
        # QTc_B = 400 / sqrt(0.8) = 447.214
        r = REGISTRY.invoke("medical.qtc_bazett", qt="400", rr="800")
        assert abs(Decimal(r["qtc"]) - Decimal("447.21359549")) < Decimal("1E-6")

    def test_unit_seconds(self) -> None:
        r = REGISTRY.invoke("medical.qtc_bazett", qt="0.4", rr="1.0", unit="s")
        assert abs(Decimal(r["qtc"]) - Decimal("0.4")) < Decimal("1E-8")

    def test_qt_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("medical.qtc_bazett", qt="-400", rr="800")


class TestFridericia:
    def test_qt_400_rr_1000(self) -> None:
        # QTc_F = 400 / 1^(1/3) = 400
        r = REGISTRY.invoke("medical.qtc_fridericia", qt="400", rr="1000")
        assert abs(Decimal(r["qtc"]) - Decimal("400")) < Decimal("1E-6")

    def test_qt_400_rr_800(self) -> None:
        # 400 / 0.8^(1/3) = 400 / 0.9283 ≈ 430.887
        r = REGISTRY.invoke("medical.qtc_fridericia", qt="400", rr="800")
        assert abs(Decimal(r["qtc"]) - Decimal("430.887")) < Decimal("1E-3")


class TestFraminghamQT:
    def test_qt_400_rr_800_ms(self) -> None:
        # QTc_s = 0.4 + 0.154 * (1 - 0.8) = 0.4 + 0.0308 = 0.4308 s -> 430.8 ms
        r = REGISTRY.invoke("medical.qtc_framingham", qt="400", rr="800")
        assert abs(Decimal(r["qtc"]) - Decimal("430.8")) < Decimal("1E-3")


class TestHodges:
    def test_qt_400_rr_800_ms(self) -> None:
        # HR = 75, QTc_ms = 400 + 1.75*(75-60) = 426.25
        r = REGISTRY.invoke("medical.qtc_hodges", qt="400", rr="800")
        assert abs(Decimal(r["qtc"]) - Decimal("426.25")) < Decimal("1E-6")
        assert abs(Decimal(r["hr_bpm"]) - Decimal("75")) < Decimal("1E-6")


class TestBatchRaceFree:
    def test_bazett_race_free(self) -> None:
        baseline = REGISTRY.invoke("medical.qtc_bazett", qt="400", rr="800")["qtc"]

        def run() -> str:
            return REGISTRY.invoke("medical.qtc_bazett", qt="400", rr="800")["qtc"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline


class TestInvalidUnit:
    def test_invalid_unit_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("medical.qtc_bazett", qt="400", rr="800", unit="foo")
