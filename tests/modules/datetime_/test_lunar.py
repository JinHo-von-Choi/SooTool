"""Tests for Korean lunar calendar, 24 solar terms, and lunar holidays."""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.datetime_  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.datetime_.lunar import _LUNAR_YEARS


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


class TestLunarTableAgainstKasi:
    """음력 조견표가 KASI 공인 한국 음력과 어긋나지 않는지 고정한다.

    2026-10-30 감사에서 _LUNAR_YEARS 의 lengths 가 2020~2030 중 11개 해에서
    한 달 길이 합이 실제 음력 연 길이와 1일 어긋나 있어(음력 월 시작일 136건 중
    47건 오류) 추석 날짜가 2027~2030 에서 틀렸던 것을 회귀 방지용이다.
    """

    # KASI 공인 조견표 기준 설날(음력 1/1)과 추석(음력 8/15) 날짜.
    SEOLLAL = {
        2020: "2020-01-25", 2021: "2021-02-12", 2022: "2022-02-01",
        2023: "2023-01-22", 2024: "2024-02-10", 2025: "2025-01-29",
        2026: "2026-02-17", 2027: "2027-02-07", 2028: "2028-01-27",
        2029: "2029-02-13", 2030: "2030-02-03",
    }
    CHUSEOK = {
        2020: "2020-10-01", 2021: "2021-09-21", 2022: "2022-09-10",
        2023: "2023-09-29", 2024: "2024-09-17", 2025: "2025-10-06",
        2026: "2026-09-25", 2027: "2027-09-15", 2028: "2028-10-03",
        2029: "2029-09-22", 2030: "2030-09-12",
    }

    @pytest.mark.parametrize(("year", "expected"), sorted(SEOLLAL.items()))
    def test_seollal_matches_kasi(self, year: int, expected: str) -> None:
        r = REGISTRY.invoke("datetime.lunar_holiday", name="seollal", year=year)
        assert r["solar_date"] == expected

    @pytest.mark.parametrize(("year", "expected"), sorted(CHUSEOK.items()))
    def test_chuseok_matches_kasi(self, year: int, expected: str) -> None:
        r = REGISTRY.invoke("datetime.lunar_holiday", name="chuseok", year=year)
        assert r["solar_date"] == expected

    def test_month_lengths_sum_matches_lunar_year_length(self) -> None:
        """한 해의 월 길이 합은 그해 설날부터 다음해 설날까지의 일수와 같아야 한다."""
        for year in sorted(_LUNAR_YEARS):
            entry = _LUNAR_YEARS[year]
            following = _LUNAR_YEARS.get(year + 1)
            if following is None:
                continue
            span = (following["solar_start"] - entry["solar_start"]).days
            assert sum(entry["lengths"]) == span, f"{year}년 음력 월 길이 합 불일치"

    def test_month_start_dates_match_kasi(self) -> None:
        """각 음력 월 1일의 양력 날짜가 KASI 조견표와 일치하는지 확인한다."""
        expected = _KASI_MONTH_STARTS
        mismatches = []
        for (year, month, is_leap), expected_date in expected.items():
            r = REGISTRY.invoke(
                "datetime.lunar_to_solar",
                lunar_year=year, lunar_month=month, lunar_day=1, is_leap=is_leap,
            )
            if r["solar_date"] != expected_date:
                mismatches.append(
                    f"{year}-{month}{'(윤)' if is_leap else ''}: "
                    f"{r['solar_date']} != {expected_date}"
                )
        assert not mismatches, "음력 월 시작일 불일치: " + ", ".join(mismatches)


# KASI 조견표 기준 음력 각 월 1일의 양력 날짜.
_KASI_MONTH_STARTS: dict[tuple[int, int, bool], str] = {
    (2020, 1, False): "2020-01-25",
    (2020, 2, False): "2020-02-24",
    (2020, 3, False): "2020-03-24",
    (2020, 4, False): "2020-04-23",
    (2020, 4, True): "2020-05-23",
    (2020, 5, False): "2020-06-21",
    (2020, 6, False): "2020-07-21",
    (2020, 7, False): "2020-08-19",
    (2020, 8, False): "2020-09-17",
    (2020, 9, False): "2020-10-17",
    (2020, 10, False): "2020-11-15",
    (2020, 11, False): "2020-12-15",
    (2020, 12, False): "2021-01-13",
    (2021, 1, False): "2021-02-12",
    (2021, 2, False): "2021-03-13",
    (2021, 3, False): "2021-04-12",
    (2021, 4, False): "2021-05-12",
    (2021, 5, False): "2021-06-10",
    (2021, 6, False): "2021-07-10",
    (2021, 7, False): "2021-08-08",
    (2021, 8, False): "2021-09-07",
    (2021, 9, False): "2021-10-06",
    (2021, 10, False): "2021-11-05",
    (2021, 11, False): "2021-12-04",
    (2021, 12, False): "2022-01-03",
    (2022, 1, False): "2022-02-01",
    (2022, 2, False): "2022-03-03",
    (2022, 3, False): "2022-04-01",
    (2022, 4, False): "2022-05-01",
    (2022, 5, False): "2022-05-30",
    (2022, 6, False): "2022-06-29",
    (2022, 7, False): "2022-07-29",
    (2022, 8, False): "2022-08-27",
    (2022, 9, False): "2022-09-26",
    (2022, 10, False): "2022-10-25",
    (2022, 11, False): "2022-11-24",
    (2022, 12, False): "2022-12-23",
    (2023, 1, False): "2023-01-22",
    (2023, 2, False): "2023-02-20",
    (2023, 2, True): "2023-03-22",
    (2023, 3, False): "2023-04-20",
    (2023, 4, False): "2023-05-20",
    (2023, 5, False): "2023-06-18",
    (2023, 6, False): "2023-07-18",
    (2023, 7, False): "2023-08-16",
    (2023, 8, False): "2023-09-15",
    (2023, 9, False): "2023-10-15",
    (2023, 10, False): "2023-11-13",
    (2023, 11, False): "2023-12-13",
    (2023, 12, False): "2024-01-11",
    (2024, 1, False): "2024-02-10",
    (2024, 2, False): "2024-03-10",
    (2024, 3, False): "2024-04-09",
    (2024, 4, False): "2024-05-08",
    (2024, 5, False): "2024-06-06",
    (2024, 6, False): "2024-07-06",
    (2024, 7, False): "2024-08-04",
    (2024, 8, False): "2024-09-03",
    (2024, 9, False): "2024-10-03",
    (2024, 10, False): "2024-11-01",
    (2024, 11, False): "2024-12-01",
    (2024, 12, False): "2024-12-31",
    (2025, 1, False): "2025-01-29",
    (2025, 2, False): "2025-02-28",
    (2025, 3, False): "2025-03-29",
    (2025, 4, False): "2025-04-28",
    (2025, 5, False): "2025-05-27",
    (2025, 6, False): "2025-06-25",
    (2025, 6, True): "2025-07-25",
    (2025, 7, False): "2025-08-23",
    (2025, 8, False): "2025-09-22",
    (2025, 9, False): "2025-10-21",
    (2025, 10, False): "2025-11-20",
    (2025, 11, False): "2025-12-20",
    (2025, 12, False): "2026-01-19",
    (2026, 1, False): "2026-02-17",
    (2026, 2, False): "2026-03-19",
    (2026, 3, False): "2026-04-17",
    (2026, 4, False): "2026-05-17",
    (2026, 5, False): "2026-06-15",
    (2026, 6, False): "2026-07-14",
    (2026, 7, False): "2026-08-13",
    (2026, 8, False): "2026-09-11",
    (2026, 9, False): "2026-10-11",
    (2026, 10, False): "2026-11-09",
    (2026, 11, False): "2026-12-09",
    (2026, 12, False): "2027-01-08",
    (2027, 1, False): "2027-02-07",
    (2027, 2, False): "2027-03-08",
    (2027, 3, False): "2027-04-07",
    (2027, 4, False): "2027-05-06",
    (2027, 5, False): "2027-06-05",
    (2027, 6, False): "2027-07-04",
    (2027, 7, False): "2027-08-02",
    (2027, 8, False): "2027-09-01",
    (2027, 9, False): "2027-09-30",
    (2027, 10, False): "2027-10-29",
    (2027, 11, False): "2027-11-28",
    (2027, 12, False): "2027-12-28",
    (2028, 1, False): "2028-01-27",
    (2028, 2, False): "2028-02-25",
    (2028, 3, False): "2028-03-26",
    (2028, 4, False): "2028-04-25",
    (2028, 5, False): "2028-05-24",
    (2028, 5, True): "2028-06-23",
    (2028, 6, False): "2028-07-22",
    (2028, 7, False): "2028-08-20",
    (2028, 8, False): "2028-09-19",
    (2028, 9, False): "2028-10-18",
    (2028, 10, False): "2028-11-16",
    (2028, 11, False): "2028-12-16",
    (2028, 12, False): "2029-01-15",
    (2029, 1, False): "2029-02-13",
    (2029, 2, False): "2029-03-15",
    (2029, 3, False): "2029-04-14",
    (2029, 4, False): "2029-05-13",
    (2029, 5, False): "2029-06-12",
    (2029, 6, False): "2029-07-12",
    (2029, 7, False): "2029-08-10",
    (2029, 8, False): "2029-09-08",
    (2029, 9, False): "2029-10-08",
    (2029, 10, False): "2029-11-06",
    (2029, 11, False): "2029-12-05",
    (2029, 12, False): "2030-01-04",
    (2030, 1, False): "2030-02-03",
    (2030, 2, False): "2030-03-04",
    (2030, 3, False): "2030-04-03",
    (2030, 4, False): "2030-05-02",
    (2030, 5, False): "2030-06-01",
    (2030, 6, False): "2030-07-01",
    (2030, 7, False): "2030-07-30",
    (2030, 8, False): "2030-08-29",
    (2030, 9, False): "2030-09-27",
    (2030, 10, False): "2030-10-27",
    (2030, 11, False): "2030-11-25",
    (2030, 12, False): "2030-12-25",
}


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
