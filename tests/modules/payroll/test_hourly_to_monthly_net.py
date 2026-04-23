"""Tests for payroll.hourly_to_monthly_net."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.hourly_to_monthly_net", **kwargs)


class TestHourlyBasic:
    def test_minimum_wage_2026(self):
        # 2026년 최저시급 10,030 기준 환산
        r = call(hourly_wage="10030", year=2026)
        assert Decimal(r["monthly_gross"]) == Decimal("2096270")  # 10030*209
        assert Decimal(r["net"]) < Decimal(r["monthly_gross"])
        assert Decimal(r["net"]) > Decimal("0")

    def test_custom_hours(self):
        r = call(hourly_wage="15000", year=2026, monthly_hours="160")
        assert Decimal(r["monthly_gross"]) == Decimal("2400000")

    def test_meal_allowance_reduces_taxable(self):
        without = call(hourly_wage="15000", year=2026)
        withm   = call(hourly_wage="15000", year=2026, meal_allowance="200000")
        # 식대 비과세만큼 과세소득 축소 → net 증가
        assert Decimal(withm["net"]) >= Decimal(without["net"])

    def test_policy_version_and_trace(self):
        r = call(hourly_wage="12000", year=2026)
        assert r["trace"]["tool"] == "payroll.hourly_to_monthly_net"
        assert r["policy_version"]["year"] == 2026
        assert "insurances" in r
        assert "taxes" in r

    def test_high_wage_insurance_cap_propagates(self):
        # 매우 높은 시급 — kr_salary 국민연금 상한 적용 확인
        r = call(hourly_wage="200000", year=2026)
        np_ = Decimal(r["insurances"]["national_pension"])
        assert np_ == Decimal("265500")  # 5,900,000 * 0.045 (10원 버림)


class TestHourlyValidation:
    def test_zero_wage_raises(self):
        with pytest.raises(InvalidInputError):
            call(hourly_wage="0", year=2026)

    def test_negative_wage_raises(self):
        with pytest.raises(InvalidInputError):
            call(hourly_wage="-1", year=2026)

    def test_zero_hours_raises(self):
        with pytest.raises(InvalidInputError):
            call(hourly_wage="10000", year=2026, monthly_hours="0")

    def test_negative_hours_raises(self):
        with pytest.raises(InvalidInputError):
            call(hourly_wage="10000", year=2026, monthly_hours="-1")

    def test_zero_dependents_raises(self):
        with pytest.raises(InvalidInputError):
            call(hourly_wage="10000", year=2026, num_dependents=0)


class TestHourlyBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"hr-{i}",
                "tool": "payroll.hourly_to_monthly_net",
                "args": {
                    "hourly_wage": "12000",
                    "year":        2026,
                    "meal_allowance": "200000",
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["net"] == first["net"]
            assert r["monthly_gross"] == first["monthly_gross"]
