"""Tests for pm.earned_schedule."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.pm  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _simple_timeline() -> list[dict[str, str]]:
    return [
        {"time": "0",  "cumulative_pv": "0"},
        {"time": "10", "cumulative_pv": "100"},
        {"time": "20", "cumulative_pv": "200"},
    ]


class TestEarnedSchedule:
    def test_on_schedule(self) -> None:
        r = REGISTRY.invoke(
            "pm.earned_schedule",
            pv_timeline=_simple_timeline(),
            earned_value="100",
            actual_time="10",
            planned_duration="20",
        )
        assert Decimal(r["es"]) == Decimal("10")
        assert Decimal(r["spi_t"]) == Decimal("1")

    def test_behind_schedule(self) -> None:
        r = REGISTRY.invoke(
            "pm.earned_schedule",
            pv_timeline=_simple_timeline(),
            earned_value="80",
            actual_time="10",
            planned_duration="20",
        )
        assert Decimal(r["es"]) == Decimal("8")
        assert Decimal(r["spi_t"]) == Decimal("0.8")
        # IEAC(t) = PD / SPI(t) = 20 / 0.8 = 25
        assert Decimal(r["ieac_t"]) == Decimal("25")

    def test_ahead_of_schedule(self) -> None:
        r = REGISTRY.invoke(
            "pm.earned_schedule",
            pv_timeline=_simple_timeline(),
            earned_value="150",
            actual_time="10",
            planned_duration="20",
        )
        assert Decimal(r["es"]) == Decimal("15")

    def test_non_monotonic_pv_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "pm.earned_schedule",
                pv_timeline=[
                    {"time": "0",  "cumulative_pv": "0"},
                    {"time": "5",  "cumulative_pv": "50"},
                    {"time": "10", "cumulative_pv": "30"},
                ],
                earned_value="40",
                actual_time="5",
                planned_duration="10",
            )

    def test_invalid_timeline_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "pm.earned_schedule",
                pv_timeline=[],
                earned_value="10",
                actual_time="5",
                planned_duration="10",
            )


class TestBatchRaceFree:
    def test_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "pm.earned_schedule",
            pv_timeline=_simple_timeline(),
            earned_value="100", actual_time="10", planned_duration="20",
        )["es"]

        def run() -> str:
            return REGISTRY.invoke(
                "pm.earned_schedule",
                pv_timeline=_simple_timeline(),
                earned_value="100", actual_time="10", planned_duration="20",
            )["es"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
