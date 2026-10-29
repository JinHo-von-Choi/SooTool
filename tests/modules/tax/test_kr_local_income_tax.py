"""Tests for tax.kr_local_income_tax."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_local_income_tax", **kwargs)


class TestLocalIncomeTaxBasic:
    def test_10_percent_rate(self):
        r = call(income_tax="1000000")
        assert Decimal(r["local_income_tax"]) == Decimal("100000")
        assert Decimal(r["rate"]) == Decimal("0.10")

    def test_rounding_down_default(self):
        r = call(income_tax="12345")
        # 12345 * 0.10 = 1234.5 → DOWN → 1234
        assert Decimal(r["local_income_tax"]) == Decimal("1234")

    def test_rounding_half_up_option(self):
        r = call(income_tax="12345", rounding="HALF_UP")
        assert Decimal(r["local_income_tax"]) == Decimal("1235")

    def test_zero_income_tax(self):
        r = call(income_tax="0")
        assert Decimal(r["local_income_tax"]) == Decimal("0")

    def test_trace_present(self):
        r = call(income_tax="500000")
        assert r["trace"]["tool"] == "tax.kr_local_income_tax"
        assert "formula" in r["trace"]


class TestLocalIncomeTaxValidation:
    def test_negative_raises(self):
        with pytest.raises(InvalidInputError):
            call(income_tax="-1")

    def test_invalid_rounding_raises(self):
        with pytest.raises(InvalidInputError):
            call(income_tax="1000", rounding="UNKNOWN")

    def test_negative_decimals_raises(self):
        with pytest.raises(InvalidInputError):
            call(income_tax="1000", decimals=-1)

    def test_large_value(self):
        r = call(income_tax="1000000000")  # 10억
        assert Decimal(r["local_income_tax"]) == Decimal("100000000")

    def test_decimals_precision(self):
        r = call(income_tax="12345", decimals=2, rounding="HALF_UP")
        assert Decimal(r["local_income_tax"]) == Decimal("1234.50")


class TestLocalIncomeTaxBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"loc-{i}",
                "tool": "tax.kr_local_income_tax",
                "args": {"income_tax": "2000000"},
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        for r in results:
            assert r["local_income_tax"] == "200000"


class TestCollectionStageTruncation:
    """징수 단계(월급 원천징수)의 지방소득세 끝수 규칙.

    「국고금 관리법」 제47조제1항: 국고금의 수입·지출에서 10원 미만의 끝수는 계산하지 아니한다.
    「지방세기본법」 제59조: 지방자치단체의 징수금 끝수 계산에 「국고금 관리법」 제47조를 준용한다.

    산출세액(「지방세법」 제92조제3항, 위 도구)과 달리 징수 단계에만 붙는 규칙이다.
    """

    def test_nts_official_example(self):
        """국세청 근로소득 원천징수영수증 예시: 소득세 9,450 -> 지방소득세 940 (945 에서 10원 미만 버림)."""
        from sootool.modules.tax.kr_local_income_tax import collection_local_income_tax

        assert collection_local_income_tax(Decimal("9450"), Decimal("0.10")) == Decimal("940")

    @pytest.mark.parametrize(
        ("income_tax", "expected"),
        [("0", "0"), ("9450", "940"), ("56850", "5680"), ("74350", "7430"), ("1000", "100")],
    )
    def test_truncates_to_ten_won(self, income_tax: str, expected: str):
        from sootool.modules.tax.kr_local_income_tax import collection_local_income_tax

        assert collection_local_income_tax(Decimal(income_tax), Decimal("0.10")) == Decimal(expected)

    def test_result_is_always_a_multiple_of_ten(self):
        from sootool.modules.tax.kr_local_income_tax import collection_local_income_tax

        for income_tax in range(0, 2000, 37):
            local = collection_local_income_tax(Decimal(income_tax), Decimal("0.10"))
            assert local % 10 == 0

    def test_salary_tool_uses_the_collection_rule(self):
        """월급 도구는 징수 단계이므로 10원 단위 버림을 적용한다."""
        r = REGISTRY.invoke("payroll.kr_salary", monthly_salary="3010000", year=2026)
        income_tax = Decimal(r["taxes"]["income_tax"])
        local      = Decimal(r["taxes"]["local_income_tax"])
        assert local == (income_tax * Decimal("0.10") // 10) * 10
        assert local != round(income_tax * Decimal("0.10")) or income_tax % 10 == 0
