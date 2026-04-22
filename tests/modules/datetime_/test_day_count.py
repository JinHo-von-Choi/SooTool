"""Tests for datetime.day_count tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.datetime_  # ensure tools are registered
from sootool.core.registry import REGISTRY


class TestDayCount30_360:
    def test_30_360_full_year(self) -> None:
        """start 2026-01-01 end 2027-01-01, 30/360 -> 360 days, year_fraction='1'."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2027-01-01",
            convention="30/360",
        )
        assert result["days"] == 360
        assert Decimal(result["year_fraction"]) == Decimal("1")
        assert "trace" in result

    def test_30_360_half_year(self) -> None:
        """start 2026-01-01 end 2026-07-01, 30/360 -> 180 days, year_fraction=0.5."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2026-07-01",
            convention="30/360",
        )
        assert result["days"] == 180
        assert Decimal(result["year_fraction"]) == Decimal("0.5")

    def test_30_360_one_month(self) -> None:
        """start 2026-01-01 end 2026-02-01, 30/360 -> 30 days."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2026-02-01",
            convention="30/360",
        )
        assert result["days"] == 30


class TestDayCountACT365:
    def test_act_365_full_year_non_leap(self) -> None:
        """2026-01-01 to 2027-01-01: 365 actual days, year_fraction=1."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2027-01-01",
            convention="ACT/365",
        )
        assert result["days"] == 365
        assert Decimal(result["year_fraction"]) == Decimal("1")

    def test_act_365_half_year(self) -> None:
        """2026-01-01 to 2026-07-01: 181 actual days, year_fraction = 181/365."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2026-07-01",
            convention="ACT/365",
        )
        assert result["days"] == 181
        expected = Decimal("181") / Decimal("365")
        assert abs(Decimal(result["year_fraction"]) - expected) < Decimal("1e-10")


class TestDayCountACTACT:
    def test_act_act_full_year_non_leap(self) -> None:
        """2026 is not a leap year; 2026-01-01 to 2027-01-01 = 365/365 = 1."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2027-01-01",
            convention="ACT/ACT",
        )
        assert result["days"] == 365
        assert Decimal(result["year_fraction"]) == Decimal("1")

    def test_act_act_leap_year(self) -> None:
        """2024 is a leap year (366 days); 2024-01-01 to 2025-01-01 = 366/366 = 1."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2024-01-01",
            end="2025-01-01",
            convention="ACT/ACT",
        )
        assert result["days"] == 366
        assert Decimal(result["year_fraction"]) == Decimal("1")


class TestDayCountACT360:
    def test_act_360_full_year_non_leap(self) -> None:
        """2026-01-01 to 2027-01-01: 365 actual days, year_fraction = 365/360."""
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2027-01-01",
            convention="ACT/360",
        )
        assert result["days"] == 365
        expected = Decimal("365") / Decimal("360")
        assert abs(Decimal(result["year_fraction"]) - expected) < Decimal("1e-10")


class TestDayCountTrace:
    def test_trace_present(self) -> None:
        result = REGISTRY.invoke(
            "datetime.day_count",
            start="2026-01-01",
            end="2026-06-01",
            convention="ACT/365",
        )
        assert result["trace"]["tool"] == "datetime.day_count"
