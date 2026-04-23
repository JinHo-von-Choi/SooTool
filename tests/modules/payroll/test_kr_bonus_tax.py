"""Tests for payroll.kr_bonus_tax."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_bonus_tax", **kwargs)


class TestBonusTaxBasic:
    def test_averaging_method_sample(self):
        r = call(
            bonus_amount="3000000", monthly_salary="3000000",
            year=2026, dependents=1, method="averaging",
        )
        assert r["method"] == "averaging"
        assert Decimal(r["bonus_tax"]) > Decimal("0")
        assert Decimal(r["combined_annual_tax"]) > Decimal(r["base_annual_tax"])

    def test_simple_method_higher_withholding(self):
        avg = call(
            bonus_amount="3000000", monthly_salary="3000000",
            year=2026, dependents=1, method="averaging",
        )
        simple = call(
            bonus_amount="3000000", monthly_salary="3000000",
            year=2026, dependents=1, method="simple",
        )
        # simple: 전체를 1회분으로 보므로 averaging 보다 크거나 같음
        assert Decimal(simple["bonus_tax"]) >= Decimal(avg["bonus_tax"])

    def test_zero_bonus_yields_zero_tax(self):
        r = call(
            bonus_amount="0", monthly_salary="3000000", year=2026,
        )
        assert Decimal(r["bonus_tax"]) == Decimal("0")

    def test_payment_period_months_affects_averaging(self):
        r6 = call(
            bonus_amount="6000000", monthly_salary="3000000",
            year=2026, method="averaging", payment_period_months=6,
        )
        r12 = call(
            bonus_amount="6000000", monthly_salary="3000000",
            year=2026, method="averaging", payment_period_months=12,
        )
        # period 6: 평균 100만/월, period 12: 50만/월 → 한계 세율은 period 6이 더 높음 기대
        assert Decimal(r6["bonus_tax"]) >= Decimal(r12["bonus_tax"])

    def test_trace_and_policy_version(self):
        r = call(
            bonus_amount="1000000", monthly_salary="3000000", year=2026,
        )
        assert r["trace"]["tool"] == "payroll.kr_bonus_tax"
        assert r["policy_version"]["year"] == 2026


class TestBonusTaxValidation:
    def test_invalid_method_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                bonus_amount="1000000", monthly_salary="3000000",
                year=2026, method="unknown",
            )

    def test_negative_bonus_raises(self):
        with pytest.raises(InvalidInputError):
            call(bonus_amount="-1", monthly_salary="3000000", year=2026)

    def test_negative_monthly_raises(self):
        with pytest.raises(InvalidInputError):
            call(bonus_amount="1000000", monthly_salary="-1", year=2026)

    def test_zero_dependents_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                bonus_amount="1000000", monthly_salary="3000000",
                year=2026, dependents=0,
            )

    def test_invalid_period_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                bonus_amount="1000000", monthly_salary="3000000",
                year=2026, payment_period_months=0,
            )
        with pytest.raises(InvalidInputError):
            call(
                bonus_amount="1000000", monthly_salary="3000000",
                year=2026, payment_period_months=13,
            )


class TestBonusTaxBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"bonus-{i}",
                "tool": "payroll.kr_bonus_tax",
                "args": {
                    "bonus_amount":   "2000000",
                    "monthly_salary": "3000000",
                    "year":           2026,
                    "method":         "averaging",
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["bonus_tax"] == first["bonus_tax"]
