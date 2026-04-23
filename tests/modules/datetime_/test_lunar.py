"""Tests for Korean lunar calendar, 24 solar terms, and lunar holidays."""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.datetime_  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestSolarToLunar:
    def test_solar_2024_02_10_is_lunar_new_year(self) -> None:
        r = REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2024-02-10")
        assert r["lunar_year"] == 2024
        assert r["lunar_month"] == 1
        assert r["lunar_day"] == 1
        assert r["is_leap"] is False

    def test_solar_2025_01_29_is_2025_lunar_new_year(self) -> None:
        r = REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2025-01-29")
        assert (r["lunar_year"], r["lunar_month"], r["lunar_day"]) == (2025, 1, 1)

    def test_solar_out_of_range_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2035-01-01")

    def test_trace(self) -> None:
        r = REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2024-02-10")
        assert r["trace"]["tool"] == "datetime.solar_to_lunar"


class TestLunarToSolar:
    def test_seollal_2024(self) -> None:
        r = REGISTRY.invoke(
            "datetime.lunar_to_solar",
            lunar_year=2024, lunar_month=1, lunar_day=1,
        )
        assert r["solar_date"] == "2024-02-10"

    def test_chuseok_2024_lunar_8_15(self) -> None:
        r = REGISTRY.invoke(
            "datetime.lunar_to_solar",
            lunar_year=2024, lunar_month=8, lunar_day=15,
        )
        # Chuseok 2024 = 2024-09-17
        assert r["solar_date"] == "2024-09-17"

    def test_invalid_month_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "datetime.lunar_to_solar",
                lunar_year=2024, lunar_month=13, lunar_day=1,
            )

    def test_invalid_leap_month_raises(self) -> None:
        # 2024 has no leap month
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "datetime.lunar_to_solar",
                lunar_year=2024, lunar_month=4, lunar_day=1, is_leap=True,
            )


class TestSolarToLunarRoundTrip:
    def test_round_trip_2025_03_15(self) -> None:
        forward = REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2025-03-15")
        back = REGISTRY.invoke(
            "datetime.lunar_to_solar",
            lunar_year=forward["lunar_year"],
            lunar_month=forward["lunar_month"],
            lunar_day=forward["lunar_day"],
            is_leap=forward["is_leap"],
        )
        assert back["solar_date"] == "2025-03-15"


class TestSolarTerms:
    def test_2026_count(self) -> None:
        r = REGISTRY.invoke("datetime.solar_terms", year=2026)
        assert r["year"] == 2026
        assert len(r["terms"]) == 24

    def test_2026_first_term_is_ipchun(self) -> None:
        r = REGISTRY.invoke("datetime.solar_terms", year=2026)
        assert r["terms"][0]["name"] == "입춘"
        assert r["terms"][0]["date"].startswith("2026-02")

    def test_invalid_year_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("datetime.solar_terms", year=0)


class TestLunarHoliday:
    def test_chuseok_2025(self) -> None:
        r = REGISTRY.invoke("datetime.lunar_holiday", name="chuseok", year=2025)
        # 2025 chuseok (음력 8/15) = 2025-10-06
        assert r["solar_date"] == "2025-10-06"

    def test_seollal_2024(self) -> None:
        r = REGISTRY.invoke("datetime.lunar_holiday", name="seollal", year=2024)
        assert r["solar_date"] == "2024-02-10"

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("datetime.lunar_holiday", name="bogus", year=2024)


class TestBatchRaceFree:
    def test_solar_to_lunar_race_free(self) -> None:
        baseline = REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2024-06-01")

        def run() -> tuple:
            r = REGISTRY.invoke("datetime.solar_to_lunar", solar_date="2024-06-01")
            return (r["lunar_year"], r["lunar_month"], r["lunar_day"], r["is_leap"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]

        key = (baseline["lunar_year"], baseline["lunar_month"],
               baseline["lunar_day"], baseline["is_leap"])
        for r in results:
            assert r == key
