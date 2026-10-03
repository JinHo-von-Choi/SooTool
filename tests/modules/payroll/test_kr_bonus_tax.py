"""Tests for payroll.kr_bonus_tax.

Author: 최진호
Modified: 2026-10-03

기대값은 소득세법 제136조제1항과 소득세법 시행령 별표 2 간이세액표(2026.3.1. 이후)에서 계산했다.
3,000~3,020천원 74,350원, 3,240~3,260천원 95,430원, 3,500~3,520천원 127,220원,
4,000~4,020천원 195,960원, 6,000~6,020천원 505,900원 (공제대상가족 1명).
"""
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
        # (간이세액(3,250,000) - 간이세액(3,000,000)) x 12 = (95,430 - 74,350) x 12
        assert r["base_monthly_tax"]     == "74350"
        assert r["combined_monthly_tax"] == "95430"
        assert r["bonus_tax"]            == "252960"
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
        # simple: 간이세액(6,000,000) - 간이세액(3,000,000) = 505,900 - 74,350
        assert simple["bonus_tax"] == "431550"
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
        # period 6: (간이세액(4,000,000) - 74,350) x 6 = (195,960 - 74,350) x 6
        assert r6["bonus_tax"] == "729660"
        assert Decimal(r6["bonus_tax"]) >= Decimal(r12["bonus_tax"])

    def test_averaging_six_months(self):
        """상여 3,000,000, 6개월: (127,220 - 74,350) x 6 = 317,220."""
        r = call(
            bonus_amount="3000000", monthly_salary="3000000",
            year=2026, method="averaging", payment_period_months=6,
        )
        assert r["bonus_tax"] == "317220"

    def test_children_reduce_both_sides(self):
        """가족 4명 자녀 1명: 3,000천원 26,690 - 20,830 = 5,860, 3,250천원 34,610 - 20,830 = 13,780."""
        r = call(
            bonus_amount="3000000", monthly_salary="3000000", year=2026,
            dependents=4, children_8_20=1, method="averaging",
        )
        assert r["base_monthly_tax"]     == "5860"
        assert r["combined_monthly_tax"] == "13780"
        assert r["bonus_tax"]            == "95040"   # (13,780 - 5,860) x 12

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
