"""Tests for accounting.ratios."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("accounting.ratios", **kwargs)


class TestRatios:
    def test_textbook_example(self):
        """유동자산 5000, 유동부채 2000, 재고 1000 등 표준 예시."""
        r = call(
            current_assets="5000", current_liabilities="2000", inventory="1000",
            total_assets="10000", total_liabilities="4000", total_equity="6000",
            net_income="500", revenue="8000",
        )
        # 유동비율 = 5000/2000 = 2.5
        assert Decimal(r["current_ratio"]) == Decimal("2.5")
        # 당좌비율 = (5000-1000)/2000 = 2.0
        assert Decimal(r["quick_ratio"]) == Decimal("2.0")
        # 부채비율 = 4000/6000 = 0.6667
        assert Decimal(r["debt_to_equity"]) == Decimal("0.6667")
        # 자기자본비율 = 6000/10000 = 0.6
        assert Decimal(r["equity_ratio"]) == Decimal("0.6")
        # ROE = 500/6000 = 0.0833
        assert Decimal(r["roe"]) == Decimal("0.0833")
        # ROA = 500/10000 = 0.05
        assert Decimal(r["roa"]) == Decimal("0.0500")
        # 순이익률 = 500/8000 = 0.0625
        assert Decimal(r["net_margin"]) == Decimal("0.0625")

    def test_trace_present(self):
        r = call(
            current_assets="5000", current_liabilities="2000", inventory="1000",
            total_assets="10000", total_liabilities="4000", total_equity="6000",
            net_income="500", revenue="8000",
        )
        assert r["trace"]["tool"] == "accounting.ratios"

    def test_zero_liabilities_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                current_assets="1000", current_liabilities="0", inventory="0",
                total_assets="1000", total_liabilities="0", total_equity="1000",
                net_income="100", revenue="500",
            )

    def test_negative_input_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                current_assets="-1", current_liabilities="100", inventory="0",
                total_assets="1000", total_liabilities="0", total_equity="1000",
                net_income="100", revenue="500",
            )
