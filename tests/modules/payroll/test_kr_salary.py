"""Tests for payroll.kr_salary."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401 — registers tool
import sootool.modules.tax  # noqa: F401 — kr_income policy reference
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_salary", **kwargs)


class TestKrSalaryBasic:
    def test_3million_with_meal(self):
        r = call(monthly_salary="3000000", year=2026, meal_allowance="200000")
        gross = Decimal(r["gross"])
        net   = Decimal(r["net"])
        assert gross == Decimal("3000000")
        assert Decimal(r["non_taxable"]) == Decimal("200000")
        assert Decimal(r["taxable"])     == Decimal("2800000")
        assert net < gross
        # sanity: deductions sum
        total_ded = (
            Decimal(r["insurances"]["total"])
            + Decimal(r["taxes"]["total"])
        )
        assert net == gross - total_ded

    def test_meal_capped_at_200k(self):
        r = call(monthly_salary="5000000", year=2026, meal_allowance="500000")
        assert Decimal(r["non_taxable"]) == Decimal("200000")
        assert Decimal(r["taxable"])     == Decimal("4800000")

    def test_national_pension_clipped_to_cap(self):
        """매우 높은 월급에서도 국민연금은 상한 5,900,000 기준으로 캡."""
        r = call(monthly_salary="20000000", year=2026, meal_allowance="0")
        np_ = Decimal(r["insurances"]["national_pension"])
        # 5,900,000 * 4.5% = 265,500 (10원 버림)
        assert np_ == Decimal("265500")

    def test_policy_version_exposed(self):
        r = call(monthly_salary="3000000", year=2026)
        pv = r["policy_version"]
        assert pv["year"] == 2026
        assert "sha256" in pv
        assert "effective_date" in pv

    def test_trace_present(self):
        r = call(monthly_salary="3000000", year=2026)
        assert "trace" in r
        assert r["trace"]["tool"] == "payroll.kr_salary"
        assert "formula" in r["trace"]


class TestKrSalaryValidation:
    def test_negative_salary_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="-100", year=2026)

    def test_zero_salary_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="0", year=2026)

    def test_negative_meal_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="3000000", year=2026, meal_allowance="-1")

    def test_meal_exceeds_salary_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="100000", year=2026, meal_allowance="200000")

    def test_zero_dependents_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="3000000", year=2026, num_dependents=0)


class TestKrSalaryBatch:
    def test_payroll_batch_race_free(self) -> None:
        """Run kr_salary in 100 parallel core.batch calls (ADR-007)."""
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"pay-{i}",
                "tool": "payroll.kr_salary",
                "args": {"monthly_salary": "3000000", "year": 2026, "meal_allowance": "200000"},
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["net"] == first["net"]
            assert r["insurances"]["total"] == first["insurances"]["total"]

    def test_payroll_thread_pool_race_free(self):
        """Also verify via bare ThreadPoolExecutor."""
        def run(_):
            return call(monthly_salary="3500000", year=2026, meal_allowance="200000")

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(run, range(50)))

        nets = {r["net"] for r in results}
        assert len(nets) == 1
