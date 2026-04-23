"""Tests for payroll.kr_medical_deduction (의료비 세액공제)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_medical_deduction", **kwargs)


class TestMedicalDeductionBasic:
    def test_below_threshold_no_credit(self):
        """총급여 5천만 × 3% = 150만. 의료비 100만 → threshold 이하 → 공제 0."""
        r = call(gross_income="50000000", general_medical="1000000", year=2026)
        assert Decimal(r["threshold"]) == Decimal("1500000")
        assert Decimal(r["deductible_expense"]) == Decimal("0")
        assert Decimal(r["total_credit"]) == Decimal("0")

    def test_general_above_threshold(self):
        """총급여 5천만, 일반의료비 300만 → deductible 150만 × 15% = 22.5만."""
        r = call(gross_income="50000000", general_medical="3000000", year=2026)
        assert Decimal(r["threshold"]) == Decimal("1500000")
        assert Decimal(r["deductible_expense"]) == Decimal("1500000")
        # gen_after_thr = 300만 - 150만 = 150만, 한도 700만 이내
        # credit = 150만 * 15% = 22.5만
        assert Decimal(r["general_credit"]) == Decimal("225000")
        assert Decimal(r["total_credit"]) == Decimal("225000")

    def test_general_above_annual_limit(self):
        """총급여 5천만, 일반 1000만 → threshold 차감 후 850만. 한도 700만 → 700만 × 15% = 105만."""
        r = call(gross_income="50000000", general_medical="10000000", year=2026)
        # gen_after_thr = 1000만 - 150만 = 850만. 한도 700만 clip.
        # credit = 700만 * 15% = 105만
        assert Decimal(r["general_credit"]) == Decimal("1050000")

    def test_infertility_30_percent(self):
        """총급여 5천만, 난임 500만 → threshold 일반 없음 → 500만 - 150만 = 350만 × 30% = 105만."""
        r = call(
            gross_income="50000000",
            general_medical="0",
            year=2026,
            infertility="5000000",
        )
        # 일반 0, 특수 0, 난임 500만. threshold 150만 차감 순서: 일반→특수→난임
        # 난임 after_thr = 500만 - 150만 = 350만
        # credit = 350만 * 30% = 105만
        assert Decimal(r["infertility_credit"]) == Decimal("1050000")
        assert Decimal(r["total_credit"]) == Decimal("1050000")

    def test_special_category_no_limit(self):
        """본인·장애인 의료비는 한도 없음."""
        r = call(
            gross_income="50000000",
            general_medical="0",
            year=2026,
            special_medical="10000000",
        )
        # special after_thr = 1000만 - 150만 = 850만. 한도 없음. × 15% = 127.5만
        assert Decimal(r["special_credit"]) == Decimal("1275000")


class TestMedicalDeductionEdgeCases:
    def test_premature_20_percent(self):
        """미숙아·선천성이상아 20%."""
        r = call(
            gross_income="50000000",
            general_medical="0",
            year=2026,
            premature="2000000",
        )
        # premature after_thr = 200만 - 150만 = 50만 × 20% = 10만
        assert Decimal(r["premature_credit"]) == Decimal("100000")

    def test_threshold_applied_in_priority_order(self):
        """일반→특수→난임→미숙아 순서로 threshold 차감."""
        r = call(
            gross_income="50000000",
            general_medical="1000000",    # 100만 (threshold 150만에 모두 소진)
            special_medical="1000000",    # 100만 → 잔여 threshold 50만 차감 후 50만 남음
            infertility="2000000",         # 200만, 잔여 threshold 0이므로 그대로
            year=2026,
        )
        # 일반: 100만 - min(100만, 150만) = 0
        # 특수: 100만 - min(100만, 50만) = 50만 × 15% = 7.5만
        # 난임: 200만 - 0 = 200만 × 30% = 60만
        assert Decimal(r["general_credit"]) == Decimal("0")
        assert Decimal(r["special_credit"]) == Decimal("75000")
        assert Decimal(r["infertility_credit"]) == Decimal("600000")
        assert Decimal(r["total_credit"]) == Decimal("675000")


class TestMedicalDeductionValidation:
    def test_negative_gross_raises(self):
        with pytest.raises(InvalidInputError):
            call(gross_income="-1", general_medical="0", year=2026)

    def test_negative_medical_raises(self):
        with pytest.raises(InvalidInputError):
            call(gross_income="50000000", general_medical="-1", year=2026)

    def test_negative_infertility_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                gross_income="50000000",
                general_medical="0",
                year=2026,
                infertility="-1",
            )

    def test_trace_and_policy_version(self):
        r = call(gross_income="50000000", general_medical="3000000", year=2026)
        assert r["trace"]["tool"] == "payroll.kr_medical_deduction"
        assert "formula" in r["trace"]
        assert r["policy_version"]["year"] == 2026
        assert r["policy_sha256"] != ""


class TestMedicalDeductionBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"med-{i}",
                "tool": "payroll.kr_medical_deduction",
                "args": {
                    "gross_income":    "50000000",
                    "general_medical": "3000000",
                    "year":            2026,
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        for r in response["results"]:
            assert r["result"]["total_credit"] == "225000"
