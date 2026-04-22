"""Tests for datetime.age and datetime.diff tools."""
from __future__ import annotations

import sootool.modules.datetime_  # noqa: F401
from sootool.core.registry import REGISTRY


class TestAge:
    def test_age_before_birthday_this_year(self) -> None:
        """birth 1990-06-15, reference 2026-03-01 -> years=35 (not yet had 2026 birthday)."""
        result = REGISTRY.invoke(
            "datetime.age",
            birth_date="1990-06-15",
            reference_date="2026-03-01",
        )
        assert result["years"] == 35
        assert "trace" in result

    def test_age_on_birthday(self) -> None:
        """birth 1990-06-15, reference 2026-06-15 -> years=36 (birthday today)."""
        result = REGISTRY.invoke(
            "datetime.age",
            birth_date="1990-06-15",
            reference_date="2026-06-15",
        )
        assert result["years"] == 36

    def test_age_after_birthday(self) -> None:
        """birth 1990-06-15, reference 2026-07-01 -> years=36."""
        result = REGISTRY.invoke(
            "datetime.age",
            birth_date="1990-06-15",
            reference_date="2026-07-01",
        )
        assert result["years"] == 36

    def test_age_months_days_present(self) -> None:
        """Response includes months and days fields."""
        result = REGISTRY.invoke(
            "datetime.age",
            birth_date="1990-06-15",
            reference_date="2026-03-01",
        )
        assert "months" in result
        assert "days" in result
        assert isinstance(result["months"], int)
        assert isinstance(result["days"], int)

    def test_age_trace(self) -> None:
        result = REGISTRY.invoke(
            "datetime.age",
            birth_date="2000-01-01",
            reference_date="2026-01-01",
        )
        assert result["trace"]["tool"] == "datetime.age"
        assert result["years"] == 26

    def test_age_newborn(self) -> None:
        """birth 2026-01-01, reference 2026-01-01 -> years=0, months=0, days=0."""
        result = REGISTRY.invoke(
            "datetime.age",
            birth_date="2026-01-01",
            reference_date="2026-01-01",
        )
        assert result["years"] == 0
        assert result["months"] == 0
        assert result["days"] == 0


class TestDiff:
    def test_diff_days(self) -> None:
        """2026-01-01 to 2026-01-11: 10 days."""
        result = REGISTRY.invoke(
            "datetime.diff",
            start="2026-01-01",
            end="2026-01-11",
            unit="days",
        )
        assert result["value"] == "10"

    def test_diff_weeks(self) -> None:
        """2026-01-01 to 2026-01-15: 14 days = 2 weeks."""
        result = REGISTRY.invoke(
            "datetime.diff",
            start="2026-01-01",
            end="2026-01-15",
            unit="weeks",
        )
        assert result["value"] == "2"

    def test_diff_years(self) -> None:
        """2026-01-01 to 2028-07-01 -> 2 full years elapsed."""
        result = REGISTRY.invoke(
            "datetime.diff",
            start="2026-01-01",
            end="2028-07-01",
            unit="years",
        )
        assert result["value"] == "2"

    def test_diff_months(self) -> None:
        """2026-01-01 to 2026-04-01: 3 months."""
        result = REGISTRY.invoke(
            "datetime.diff",
            start="2026-01-01",
            end="2026-04-01",
            unit="months",
        )
        assert result["value"] == "3"

    def test_diff_trace(self) -> None:
        result = REGISTRY.invoke(
            "datetime.diff",
            start="2026-01-01",
            end="2026-06-01",
            unit="days",
        )
        assert "trace" in result
        assert result["trace"]["tool"] == "datetime.diff"
