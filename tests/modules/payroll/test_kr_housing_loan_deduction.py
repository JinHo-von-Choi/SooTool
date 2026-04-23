"""Tests for payroll.kr_housing_loan_deduction (장기주택저당차입금 이자상환액 소득공제)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_housing_loan_deduction", **kwargs)


class TestHousingLoanDeductionBasic:
    def test_15plus_fixed_nongrace_max_limit(self):
        """15년 이상 고정금리+비거치식 → 한도 2000만."""
        r = call(
            interest_paid="15000000",
            term_years=20,
            is_fixed_rate=True,
            is_non_grace=True,
            year=2026,
        )
        assert r["limit_key"] == "15+_fixed_nongrace"
        assert Decimal(r["limit"]) == Decimal("20000000")
        # 이자 1500만 < 한도 2000만 → 전액
        assert Decimal(r["deductible_amount"]) == Decimal("15000000")

    def test_15plus_fixed_only(self):
        """15년 이상 고정금리 only → 한도 1800만."""
        r = call(
            interest_paid="20000000",
            term_years=20,
            is_fixed_rate=True,
            is_non_grace=False,
            year=2026,
        )
        assert r["limit_key"] == "15+_fixed_or_ng"
        assert Decimal(r["limit"]) == Decimal("18000000")
        # 2000만 > 1800만 한도 → 1800만
        assert Decimal(r["deductible_amount"]) == Decimal("18000000")

    def test_15plus_nongrace_only(self):
        """15년 이상 비거치식 only → 한도 1800만."""
        r = call(
            interest_paid="1000000",
            term_years=15,
            is_fixed_rate=False,
            is_non_grace=True,
            year=2026,
        )
        assert r["limit_key"] == "15+_fixed_or_ng"
        assert Decimal(r["deductible_amount"]) == Decimal("1000000")

    def test_15plus_other(self):
        """15년 이상 기타 조건 → 한도 500만."""
        r = call(
            interest_paid="10000000",
            term_years=20,
            is_fixed_rate=False,
            is_non_grace=False,
            year=2026,
        )
        assert r["limit_key"] == "15+_other"
        assert Decimal(r["limit"]) == Decimal("5000000")
        # 1000만 > 500만 한도 → 500만
        assert Decimal(r["deductible_amount"]) == Decimal("5000000")

    def test_10_to_15_fixed_or_nongrace(self):
        """10~15년 고정금리 또는 비거치식 → 한도 300만."""
        r = call(
            interest_paid="5000000",
            term_years=12,
            is_fixed_rate=True,
            is_non_grace=False,
            year=2026,
        )
        assert r["limit_key"] == "10_15_fixed_or_ng"
        assert Decimal(r["limit"]) == Decimal("3000000")
        assert Decimal(r["deductible_amount"]) == Decimal("3000000")


class TestHousingLoanDeductionIneligible:
    def test_10_to_15_other_no_deduction(self):
        """10~15년 기타 조건은 공제 대상 아님."""
        r = call(
            interest_paid="5000000",
            term_years=12,
            is_fixed_rate=False,
            is_non_grace=False,
            year=2026,
        )
        assert r["limit_key"] == ""
        assert Decimal(r["deductible_amount"]) == Decimal("0")
        assert Decimal(r["limit"]) == Decimal("0")

    def test_under_10_years_no_deduction(self):
        """10년 미만은 공제 대상 아님."""
        r = call(
            interest_paid="5000000",
            term_years=5,
            is_fixed_rate=True,
            is_non_grace=True,
            year=2026,
        )
        assert r["limit_key"] == ""
        assert Decimal(r["deductible_amount"]) == Decimal("0")


class TestHousingLoanDeductionValidation:
    def test_negative_interest_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                interest_paid="-1",
                term_years=20,
                is_fixed_rate=True,
                is_non_grace=True,
                year=2026,
            )

    def test_negative_term_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                interest_paid="1000000",
                term_years=-1,
                is_fixed_rate=True,
                is_non_grace=True,
                year=2026,
            )

    def test_zero_interest_no_deduction(self):
        r = call(
            interest_paid="0",
            term_years=20,
            is_fixed_rate=True,
            is_non_grace=True,
            year=2026,
        )
        assert Decimal(r["deductible_amount"]) == Decimal("0")

    def test_trace_and_policy_version(self):
        r = call(
            interest_paid="1000000",
            term_years=20,
            is_fixed_rate=True,
            is_non_grace=True,
            year=2026,
        )
        assert r["trace"]["tool"] == "payroll.kr_housing_loan_deduction"
        assert "formula" in r["trace"]
        assert r["policy_version"]["year"] == 2026
        assert r["policy_sha256"] != ""


class TestHousingLoanDeductionBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"hl-{i}",
                "tool": "payroll.kr_housing_loan_deduction",
                "args": {
                    "interest_paid": "15000000",
                    "term_years":    20,
                    "is_fixed_rate": True,
                    "is_non_grace":  True,
                    "year":          2026,
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        for r in response["results"]:
            assert r["result"]["deductible_amount"] == "15000000"
