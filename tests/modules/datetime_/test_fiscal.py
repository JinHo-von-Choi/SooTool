"""Tests for fiscal year, fiscal quarter, tax period, payroll period."""
from __future__ import annotations

import concurrent.futures

import pytest

import sootool.modules.datetime_  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestFiscalYear:
    def test_kr_calendar_year(self) -> None:
        r = REGISTRY.invoke("datetime.fiscal_year", as_of="2026-05-15", country="KR")
        assert r["fiscal_year"] == 2026
        assert r["start_date"] == "2026-01-01"
        assert r["end_date"]   == "2026-12-31"

    def test_jp_starts_april(self) -> None:
        r = REGISTRY.invoke("datetime.fiscal_year", as_of="2026-05-15", country="JP")
        assert r["fiscal_year"] == 2026
        assert r["start_date"] == "2026-04-01"
        assert r["end_date"]   == "2027-03-31"

    def test_jp_before_april_uses_prev(self) -> None:
        r = REGISTRY.invoke("datetime.fiscal_year", as_of="2026-03-15", country="JP")
        assert r["fiscal_year"] == 2025
        assert r["start_date"] == "2025-04-01"
        assert r["end_date"]   == "2026-03-31"

    def test_uk_starts_april_6(self) -> None:
        r = REGISTRY.invoke("datetime.fiscal_year", as_of="2026-07-10", country="UK")
        assert r["fiscal_year"] == 2026
        assert r["start_date"] == "2026-04-06"
        assert r["end_date"]   == "2027-04-05"

    def test_invalid_country_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("datetime.fiscal_year", as_of="2026-05-15", country="CN")


class TestFiscalQuarter:
    def test_kr_q3(self) -> None:
        r = REGISTRY.invoke("datetime.fiscal_quarter", as_of="2026-09-15", country="KR")
        assert r["quarter"] == 3
        assert r["start_date"] == "2026-07-01"
        assert r["end_date"]   == "2026-09-30"

    def test_jp_q1(self) -> None:
        r = REGISTRY.invoke("datetime.fiscal_quarter", as_of="2026-05-15", country="JP")
        assert r["quarter"] == 1
        assert r["start_date"] == "2026-04-01"
        # Q1 end = 2026-06-30
        assert r["end_date"]   == "2026-06-30"


class TestTaxPeriodKR:
    def test_calendar_year(self) -> None:
        r = REGISTRY.invoke("datetime.tax_period_kr", as_of="2026-07-15")
        assert r["tax_year"] == 2026
        assert r["start_date"] == "2026-01-01"
        assert r["end_date"]   == "2026-12-31"


class TestPayrollPeriod:
    def test_default_month(self) -> None:
        r = REGISTRY.invoke("datetime.payroll_period", as_of="2026-04-20")
        assert r["period_start"] == "2026-04-01"
        assert r["period_end"]   == "2026-04-30"

    def test_start_day_15(self) -> None:
        r = REGISTRY.invoke("datetime.payroll_period", as_of="2026-04-20", start_day=15)
        assert r["period_start"] == "2026-04-15"
        assert r["period_end"]   == "2026-05-14"

    def test_start_day_15_before(self) -> None:
        r = REGISTRY.invoke("datetime.payroll_period", as_of="2026-04-05", start_day=15)
        assert r["period_start"] == "2026-03-15"
        assert r["period_end"]   == "2026-04-14"

    def test_invalid_start_day_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("datetime.payroll_period", as_of="2026-04-05", start_day=30)


class TestBatchRaceFree:
    def test_fiscal_year_race_free(self) -> None:
        baseline = REGISTRY.invoke("datetime.fiscal_year", as_of="2026-05-15", country="JP")

        def run() -> tuple:
            r = REGISTRY.invoke("datetime.fiscal_year", as_of="2026-05-15", country="JP")
            return (r["fiscal_year"], r["start_date"], r["end_date"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]

        key = (baseline["fiscal_year"], baseline["start_date"], baseline["end_date"])
        for r in results:
            assert r == key
