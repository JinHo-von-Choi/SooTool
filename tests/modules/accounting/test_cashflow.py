"""Tests for accounting.cashflow_operating."""
from __future__ import annotations

from decimal import Decimal, Inexact, localcontext

import pytest

import sootool.modules.accounting  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("accounting.cashflow_operating", **kwargs)


class TestCFO:
    def test_zero_boundary(self):
        r = call(net_income="0")
        assert Decimal(r["cfo"]) == 0
        assert all(Decimal(value) == 0 for value in r["breakdown"].values())

    def test_negative_income_and_working_capital_decreases(self):
        r = call(
            net_income="-100",
            change_in_receivables="-20",
            change_in_inventory="-30",
            change_in_payables="-10",
            change_in_other_wc="-5",
        )
        assert r["cfo"] == "-65"
        assert r["breakdown"]["working_capital"] == "35"
        assert r["breakdown"]["receivables_adj"] == "20"

    @pytest.mark.parametrize("precision", [6, 50])
    def test_exact_cancellation_independent_of_decimal_context(self, precision):
        large = "1" + "0" * 70
        with localcontext() as ctx:
            ctx.prec = precision
            ctx.traps[Inexact] = True
            ctx.clear_flags()
            r = call(
                net_income=large,
                depreciation="0.01",
                change_in_receivables=large,
                change_in_inventory="0.001",
            )
            assert ctx.prec == precision
            assert not ctx.flags[Inexact]
        assert r["cfo"] == "0.009"
        assert r["breakdown"]["noncash_add"] == "0.01"
        assert Decimal(r["breakdown"]["working_capital"]) == Decimal("-" + large + ".001")
        assert Decimal(r["breakdown"]["receivables_adj"]) == Decimal("-" + large)

    def test_carry_across_all_inputs(self):
        r = call(
            net_income="9.99", depreciation="9.99", amortization="9.99",
            other_noncash="9.99", change_in_receivables="-9.99",
            change_in_inventory="-9.99", change_in_payables="9.99",
            change_in_other_wc="9.99",
        )
        assert r["cfo"] == "79.92"

    @pytest.mark.parametrize("field", [
        "net_income", "depreciation", "amortization", "other_noncash",
        "change_in_receivables", "change_in_inventory", "change_in_payables",
        "change_in_other_wc",
    ])
    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "invalid"])
    def test_invalid_amounts(self, field, value):
        kwargs = {"net_income": "0", field: value}
        with pytest.raises(InvalidInputError):
            call(**kwargs)

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
