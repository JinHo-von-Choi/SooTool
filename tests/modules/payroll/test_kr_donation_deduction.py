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
        """특례기부금 500만 × 15% = 75만."""
        r = call(earned_income="50000000", year=2026, legal_donation="5000000")
        assert Decimal(r["legal_credit"]) == Decimal("750000")
        assert Decimal(r["total_credit"]) == Decimal("750000")

    def test_legal_high_tier(self):
        """특례 2000만: 1천만 × 15% + 1천만 × 30% = 150만 + 300만 = 450만."""
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
        """특례+일반+정치자금 동시."""
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

    def test_legal_and_designated_share_one_tier(self):
        """특례 1500만 + 일반 1500만 합계 3000만에 15%/30% 한 번 적용 (소득세법 §59의4④).

        합계: 1000만 × 15% + 2000만 × 30% = 750만.
        특례 먼저: 1000만 × 15% + 500만 × 30% = 300만, 일반 = 750만 - 300만 = 450만.
        """
        r = call(
            earned_income="100000000",
            year=2026,
            legal_donation="15000000",
            designated_donation="15000000",
        )
        assert Decimal(r["legal_credit"]) == Decimal("3000000")
        assert Decimal(r["designated_credit"]) == Decimal("4500000")
        assert Decimal(r["total_credit"]) == Decimal("7500000")


class TestDonationDeductionLimits:
    def test_legal_limited_by_income(self):
        """특례기부금 한도 = 소득금액 - 이월결손금 (시행령 §81④1). 소득 1000만, 특례 1500만 → 1000만 × 15%."""
        r = call(earned_income="10000000", year=2026, legal_donation="15000000")
        assert Decimal(r["legal_qualifying"]) == Decimal("10000000")
        assert Decimal(r["legal_credit"]) == Decimal("1500000")

    def test_political_precedes_legal_in_limit(self):
        """소득 1000만, 정치자금 400만이 먼저 한도를 쓰고 특례는 600만까지 (시행령 §81④)."""
        r = call(
            earned_income="10000000",
            year=2026,
            legal_donation="10000000",
            political_donation="4000000",
        )
        assert Decimal(r["legal_qualifying"]) == Decimal("6000000")
        assert Decimal(r["legal_credit"]) == Decimal("900000")
        # 정치자금: 10만 × 100/110 → 90909, (400만 - 10만) × 15% = 58.5만
        assert Decimal(r["political_small_credit"]) == Decimal("90909")
        assert Decimal(r["political_credit"]) == Decimal("585000")

    def test_designated_base_excludes_legal(self):
        """일반기부금 한도 기준에서 특례기부금을 뺀다 (시행령 §81④3).

        소득 5000만, 특례 2000만 → 기준 3000만 × 30% = 900만.
        합계 2900만: 1000만 × 15% + 1900만 × 30% = 720만, 특례 450만, 일반 270만.
        """
        r = call(
            earned_income="50000000",
            year=2026,
            legal_donation="20000000",
            designated_donation="20000000",
        )
        assert Decimal(r["designated_limit"]) == Decimal("9000000")
        assert Decimal(r["legal_credit"]) == Decimal("4500000")
        assert Decimal(r["designated_credit"]) == Decimal("2700000")
        assert Decimal(r["total_credit"]) == Decimal("7200000")

    def test_religious_limit(self):
        """종교단체 기부가 있으면 기준 × 10% + min(기준 × 20%, 종교단체 외) (소득세법 §59의4④2가).

        소득 5000만, 종교 1000만, 종교 외 200만 → 한도 500만 + 200만 = 700만 × 15% = 105만.
        """
        r = call(
            earned_income="50000000",
            year=2026,
            designated_donation="2000000",
            religious_donation="10000000",
        )
        assert Decimal(r["designated_limit"]) == Decimal("7000000")
        assert Decimal(r["designated_qualifying"]) == Decimal("7000000")
        assert Decimal(r["designated_credit"]) == Decimal("1050000")

    def test_carryover_loss_reduces_base(self):
        """이월결손금 2000만 → 기준 3000만 × 30% = 900만 × 15% = 135만."""
        r = call(
            earned_income="50000000",
            year=2026,
            designated_donation="20000000",
            carryover_loss="20000000",
        )
        assert Decimal(r["designated_credit"]) == Decimal("1350000")

    def test_hometown_and_esop_reduce_base(self):
        """고향사랑 500만, 우리사주 500만 → 기준 4000만 × 30% = 1200만.

        1000만 × 15% + 200만 × 30% = 210만.
        """
        r = call(
            earned_income="50000000",
            year=2026,
            designated_donation="20000000",
            hometown_donation="5000000",
            esop_donation="5000000",
        )
        assert Decimal(r["designated_limit"]) == Decimal("12000000")
        assert Decimal(r["designated_credit"]) == Decimal("2100000")

    def test_political_high_tier_25_percent(self):
        """정치자금 5000만: 10만 × 100/110 + 3000만 × 15% + 1990만 × 25% (조특법 §76①)."""
        r = call(earned_income="100000000", year=2026, political_donation="50000000")
        assert Decimal(r["political_small_credit"]) == Decimal("90909")
        assert Decimal(r["political_credit"]) == Decimal("9475000")
        assert Decimal(r["total_credit"]) == Decimal("9565909")


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

    def test_negative_religious_raises(self):
        with pytest.raises(InvalidInputError):
            call(earned_income="50000000", year=2026, religious_donation="-1")

    def test_negative_carryover_loss_raises(self):
        with pytest.raises(InvalidInputError):
            call(earned_income="50000000", year=2026, carryover_loss="-1")

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
