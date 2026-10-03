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
    def test_hourly_10030_conversion(self):
        # 시급 10,030 x 209시간
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
        # 매우 높은 시급: kr_salary 국민연금 기준소득월액 상한 적용 확인
        r = call(hourly_wage="200000", year=2026)
        np_ = Decimal(r["insurances"]["national_pension"])
        assert np_ == Decimal("313025")  # 6,590,000 * 0.0475 (2026.7.1. 이후 상한)
        r = call(hourly_wage="200000", year=2026, as_of="2026-05-01")
        assert Decimal(r["insurances"]["national_pension"]) == Decimal("302575")  # 6,370,000 * 0.0475

    def test_children_8_20_passed_to_salary(self):
        """15,000 x 200 = 3,000,000: 간이세액표 3,000~3,020천원, 가족 4명 26,690, 자녀 1명 차감 20,830."""
        r = call(hourly_wage="15000", year=2026, monthly_hours="200", num_dependents=4, children_8_20=1)
        assert Decimal(r["taxes"]["income_tax"]) == Decimal("5860")


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
