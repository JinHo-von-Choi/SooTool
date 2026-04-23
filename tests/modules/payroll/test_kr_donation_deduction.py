"""Tests for payroll.kr_donation_deduction (기부금 세액공제)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_donation_deduction", **kwargs)


class TestDonationDeductionBasic:
    def test_legal_low_tier(self):
        """법정기부금 500만 × 15% = 75만."""
        r = call(earned_income="50000000", year=2026, legal_donation="5000000")
        assert Decimal(r["legal_credit"]) == Decimal("750000")
        assert Decimal(r["total_credit"]) == Decimal("750000")

    def test_legal_high_tier(self):
        """법정 2000만: 1천만 × 15% + 1천만 × 30% = 150만 + 300만 = 450만."""
        r = call(earned_income="100000000", year=2026, legal_donation="20000000")
        assert Decimal(r["legal_credit"]) == Decimal("4500000")

    def test_designated_limited_by_earned_income(self):
        """근로소득 5천만 × 30% = 1500만 한도. 지정기부금 2000만 → 1500만만 인정."""
        r = call(
            earned_income="50000000",
            year=2026,
            designated_donation="20000000",
        )
        # qualifying = 1500만 (한도). 1천만×15% + 500만×30% = 150만 + 150만 = 300만
        assert Decimal(r["designated_credit"]) == Decimal("3000000")

    def test_designated_within_limit(self):
        """지정 500만, 근로소득 1억(3천만 한도) → 500만 전액 × 15% = 75만."""
        r = call(
            earned_income="100000000",
            year=2026,
            designated_donation="5000000",
        )
        assert Decimal(r["designated_credit"]) == Decimal("750000")

    def test_political_small_amount(self):
        """정치자금 10만원 → 10만 × 100/110 ≈ 9만909."""
        r = call(
            earned_income="50000000",
            year=2026,
            political_donation="100000",
        )
        # 90909.09... → DOWN → 90909
        assert Decimal(r["political_small_credit"]) == Decimal("90909")
        assert Decimal(r["political_credit"]) == Decimal("0")


class TestDonationDeductionCombined:
    def test_political_above_small_cap(self):
        """정치자금 30만 → 10만 환급공제 + 20만 × 15% = 9만909 + 3만 = 12만909."""
        r = call(
            earned_income="50000000",
            year=2026,
            political_donation="300000",
        )
        assert Decimal(r["political_small_credit"]) == Decimal("90909")
        # 20만 × 15% = 3만
        assert Decimal(r["political_credit"]) == Decimal("30000")
        assert Decimal(r["total_credit"]) == Decimal("120909")

    def test_all_categories_combined(self):
        """법정+지정+정치자금 동시."""
        r = call(
            earned_income="100000000",
            year=2026,
            legal_donation="5000000",
            designated_donation="3000000",
            political_donation="50000",
        )
        # legal: 500만 × 15% = 75만
        # designated: 300만 × 15% = 45만 (한도 3000만 이내)
        # political small: 5만 × 0.9090909091 → 45454.54... → DOWN → 45454
        assert Decimal(r["legal_credit"]) == Decimal("750000")
        assert Decimal(r["designated_credit"]) == Decimal("450000")
        assert Decimal(r["political_small_credit"]) == Decimal("45454")


class TestDonationDeductionValidation:
    def test_negative_earned_income_raises(self):
        with pytest.raises(InvalidInputError):
            call(earned_income="-1", year=2026, legal_donation="100000")

    def test_negative_legal_raises(self):
        with pytest.raises(InvalidInputError):
            call(earned_income="50000000", year=2026, legal_donation="-1")

    def test_negative_designated_raises(self):
        with pytest.raises(InvalidInputError):
            call(earned_income="50000000", year=2026, designated_donation="-1")

    def test_negative_political_raises(self):
        with pytest.raises(InvalidInputError):
            call(earned_income="50000000", year=2026, political_donation="-1")

    def test_trace_and_policy_version(self):
        r = call(earned_income="50000000", year=2026, legal_donation="1000000")
        assert r["trace"]["tool"] == "payroll.kr_donation_deduction"
        assert r["policy_version"]["year"] == 2026
        assert r["policy_sha256"] != ""
        assert "policy_source" in r


class TestDonationDeductionBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"don-{i}",
                "tool": "payroll.kr_donation_deduction",
                "args": {
                    "earned_income":  "50000000",
                    "year":           2026,
                    "legal_donation": "5000000",
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        for r in response["results"]:
            assert r["result"]["total_credit"] == "750000"
