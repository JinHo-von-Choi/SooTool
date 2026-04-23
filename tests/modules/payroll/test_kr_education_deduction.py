"""Tests for payroll.kr_education_deduction (교육비 세액공제)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_education_deduction", **kwargs)


class TestEducationDeductionBasic:
    def test_self_no_limit(self):
        """본인 교육비 1000만 → 한도 없음 × 15% = 150만."""
        r = call(expenses={"self": "10000000"}, year=2026)
        cat = r["per_category"]["self"]
        assert cat["expense"] == "10000000"
        assert cat["qualifying"] == "10000000"
        assert cat["credit"] == "1500000"
        assert Decimal(r["total_credit"]) == Decimal("1500000")

    def test_elementary_child_limit(self):
        """자녀 초등 교육비 500만 → 300만 한도 × 15% = 45만."""
        r = call(
            expenses={"elementary": "5000000"},
            year=2026,
            counts={"elementary": 1},
        )
        cat = r["per_category"]["elementary"]
        assert Decimal(cat["qualifying"]) == Decimal("3000000")
        assert Decimal(cat["credit"]) == Decimal("450000")
        assert Decimal(r["total_credit"]) == Decimal("450000")

    def test_university_900_limit(self):
        """대학생 교육비 1000만 → 900만 한도 × 15% = 135만."""
        r = call(
            expenses={"university": "10000000"},
            year=2026,
            counts={"university": 1},
        )
        cat = r["per_category"]["university"]
        assert Decimal(cat["qualifying"]) == Decimal("9000000")
        assert Decimal(cat["credit"]) == Decimal("1350000")

    def test_multiple_children_scaling(self):
        """초·중·고 자녀 2명 합산 500만 → 한도 600만 이내 → 전액 공제."""
        r = call(
            expenses={"middle_high": "5000000"},
            year=2026,
            counts={"middle_high": 2},
        )
        cat = r["per_category"]["middle_high"]
        assert Decimal(cat["qualifying"]) == Decimal("5000000")
        assert Decimal(cat["credit"]) == Decimal("750000")

    def test_disabled_special_no_limit(self):
        """장애인 특수교육비 2000만 → 한도 없음 × 15% = 300만."""
        r = call(
            expenses={"disabled_special": "20000000"},
            year=2026,
        )
        cat = r["per_category"]["disabled_special"]
        assert cat["qualifying"] == "20000000"
        assert Decimal(cat["credit"]) == Decimal("3000000")


class TestEducationDeductionCombined:
    def test_combined_categories(self):
        """본인 500만 + 대학 900만 = 210만 공제."""
        r = call(
            expenses={"self": "5000000", "university": "9000000"},
            year=2026,
            counts={"university": 1},
        )
        # self: 500만 × 15% = 75만
        # university: 900만 × 15% = 135만
        assert Decimal(r["per_category"]["self"]["credit"]) == Decimal("750000")
        assert Decimal(r["per_category"]["university"]["credit"]) == Decimal("1350000")
        assert Decimal(r["total_credit"]) == Decimal("2100000")


class TestEducationDeductionValidation:
    def test_expenses_not_dict_raises(self):
        with pytest.raises(InvalidInputError):
            call(expenses="100000", year=2026)

    def test_unknown_category_raises(self):
        with pytest.raises(InvalidInputError):
            call(expenses={"phd": "5000000"}, year=2026)

    def test_negative_expense_raises(self):
        with pytest.raises(InvalidInputError):
            call(expenses={"self": "-1"}, year=2026)

    def test_negative_count_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                expenses={"elementary": "1000000"},
                year=2026,
                counts={"elementary": -1},
            )

    def test_trace_and_policy_version(self):
        r = call(expenses={"self": "1000000"}, year=2026)
        assert r["trace"]["tool"] == "payroll.kr_education_deduction"
        assert r["policy_version"]["year"] == 2026
        assert r["policy_sha256"] != ""
        assert "policy_source" in r


class TestEducationDeductionBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"edu-{i}",
                "tool": "payroll.kr_education_deduction",
                "args": {
                    "expenses": {"self": "1000000"},
                    "year":     2026,
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        for r in response["results"]:
            assert r["result"]["total_credit"] == "150000"
