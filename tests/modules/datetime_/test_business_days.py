"""Tests for datetime.add_business_days and datetime.count_business_days."""
from __future__ import annotations

import sootool.modules.datetime_  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.registry import REGISTRY


class TestAddBusinessDays:
    def test_add_1_day_skips_weekend(self) -> None:
        """2026-01-02 (Friday) + 1 business day -> 2026-01-05 (Monday)."""
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-01-02",
            days=1,
            country="KR",
        )
        assert result["end_date"] == "2026-01-05"
        assert "trace" in result

    def test_add_zero_days_same_date(self) -> None:
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-01-05",
            days=0,
            country="KR",
        )
        assert result["end_date"] == "2026-01-05"

    def test_add_5_days_skips_weekend(self) -> None:
        """2026-01-05 (Monday) + 5 business days -> 2026-01-12 (Monday)."""
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-01-05",
            days=5,
            country="KR",
        )
        assert result["end_date"] == "2026-01-12"

    def test_kr_substitute_holiday_2026_mar_2(self) -> None:
        """삼일절(Mar 1, Sunday) -> 대체공휴일 Mar 2 (Monday) is also a holiday.
        Adding 1 business day from 2026-02-27 (Friday) should skip Mon Mar 2.
        Result: 2026-03-03 (Tuesday).
        """
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-02-27",
            days=1,
            country="KR",
        )
        # Feb 27 Fri -> next business day skips weekend (28 Sat, Mar 1 Sun=holiday, Mar 2 Mon=substitute holiday)
        # So next business day is Mar 3 (Tue)
        assert result["end_date"] == "2026-03-03"

    def test_kr_liberation_day_substitute_aug_17(self) -> None:
        """광복절 Aug 15 (Saturday) -> 대체공휴일 Aug 17 (Monday).
        Aug 14 (Friday) + 1 business day -> skip weekend + Aug 17 substitute -> Aug 18 (Tuesday).
        """
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-08-14",
            days=1,
            country="KR",
        )
        assert result["end_date"] == "2026-08-18"

    def test_extra_holidays(self) -> None:
        """Custom extra holiday: a normally-working Tuesday becomes a holiday."""
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-01-05",
            days=1,
            country="KR",
            extra_holidays=["2026-01-06"],
        )
        # Jan 5 Mon + 1 day; Jan 6 Tue is extra holiday, so skip to Jan 7 Wed
        assert result["end_date"] == "2026-01-07"

    def test_trace_fields(self) -> None:
        result = REGISTRY.invoke(
            "datetime.add_business_days",
            start_date="2026-01-05",
            days=2,
            country="KR",
        )
        assert result["trace"]["tool"] == "datetime.add_business_days"


class TestCountBusinessDays:
    def test_count_mon_to_fri(self) -> None:
        """2026-01-05 to 2026-01-09 (Mon-Fri) = 5 days."""
        result = REGISTRY.invoke(
            "datetime.count_business_days",
            start="2026-01-05",
            end="2026-01-09",
            country="KR",
        )
        assert result["count"] == 5

    def test_count_same_day(self) -> None:
        result = REGISTRY.invoke(
            "datetime.count_business_days",
            start="2026-01-05",
            end="2026-01-05",
            country="KR",
        )
        assert result["count"] == 1

    def test_count_skips_weekend(self) -> None:
        """Mon 2026-01-05 to Mon 2026-01-12 inclusive = 6 business days (Mon-Fri + Mon)."""
        result = REGISTRY.invoke(
            "datetime.count_business_days",
            start="2026-01-05",
            end="2026-01-12",
            country="KR",
        )
        assert result["count"] == 6

    def test_count_skips_kr_holiday(self) -> None:
        """Jan 1 is New Year holiday. Mon Dec 29 to Fri Jan 2 2026:
        Dec 29 Mon, Dec 30 Tue, Dec 31 Wed, Jan 1 Thu (holiday), Jan 2 Fri = 4 days."""
        result = REGISTRY.invoke(
            "datetime.count_business_days",
            start="2025-12-29",
            end="2026-01-02",
            country="KR",
        )
        assert result["count"] == 4

    def test_trace(self) -> None:
        result = REGISTRY.invoke(
            "datetime.count_business_days",
            start="2026-01-05",
            end="2026-01-09",
            country="KR",
        )
        assert "trace" in result


class TestDatetimeCoreBatchRaceFree:
    def test_datetime_core_batch_race_free(self) -> None:
        """100 parallel calls to add_business_days; identical inputs -> identical results."""
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"item-{i}",
                "tool": "datetime.add_business_days",
                "args": {
                    "start_date": "2026-01-05",
                    "days":       5,
                    "country":    "KR",
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"]["end_date"] for r in response["results"]]
        assert all(d == results[0] for d in results)
