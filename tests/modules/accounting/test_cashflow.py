"""Tests for accounting.cashflow_operating."""
from __future__ import annotations

from decimal import Decimal

import sootool.modules.accounting  # noqa: F401
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("accounting.cashflow_operating", **kwargs)


class TestCFO:
    def test_basic_cfo(self):
        """NI 1000 + DA 200 - AR증가 100 + AP증가 50 = 1150"""
        r = call(
            net_income="1000",
            depreciation="200",
            change_in_receivables="100",
            change_in_payables="50",
        )
        assert Decimal(r["cfo"]) == Decimal("1150")

    def test_all_zero_nonincome(self):
        r = call(net_income="1000")
        assert Decimal(r["cfo"]) == Decimal("1000")

    def test_full_breakdown(self):
        r = call(
            net_income="2000",
            depreciation="300",
            amortization="100",
            other_noncash="50",
            change_in_receivables="200",
            change_in_inventory="150",
            change_in_payables="100",
            change_in_other_wc="20",
        )
        # 2000 + 300+100+50 + (-200)+(-150)+100+20 = 2220
        assert Decimal(r["cfo"]) == Decimal("2220")

    def test_breakdown_fields(self):
        r = call(net_income="1000", depreciation="200")
        assert "breakdown" in r
        assert r["breakdown"]["net_income"] == "1000"

    def test_trace(self):
        r = call(net_income="1000")
        assert r["trace"]["tool"] == "accounting.cashflow_operating"
