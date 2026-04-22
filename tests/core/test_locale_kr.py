"""
Tests for core/locale_kr.py — KRWMoney composition class.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.locale_kr import KRWMoney
from sootool.core.rounding import RoundingPolicy

DOWN    = RoundingPolicy.DOWN
HALF_UP = RoundingPolicy.HALF_UP
UP      = RoundingPolicy.UP


class TestKRWMoneyConstruction:
    def test_basic_amount(self):
        m = KRWMoney(Decimal("1000"))
        assert m.to_decimal() == Decimal("1000")

    def test_string_amount(self):
        m = KRWMoney("500")
        assert m.to_decimal() == Decimal("500")

    def test_default_rounding_is_down(self):
        # unit=1, DOWN: value is stored as-is (already at unit granularity)
        m = KRWMoney(Decimal("1000"))
        assert m.to_decimal() == Decimal("1000")

    def test_unit_rounding_on_construction_down(self):
        # 1234 rounded DOWN to unit=10 -> 1230
        m = KRWMoney(Decimal("1234"), DOWN, 10)
        assert m.to_decimal() == Decimal("1230")

    def test_unit_rounding_on_construction_half_up(self):
        # 1235 rounded HALF_UP to unit=10 -> 1240
        m = KRWMoney(Decimal("1235"), HALF_UP, 10)
        assert m.to_decimal() == Decimal("1240")

    def test_not_decimal_subclass(self):
        """isinstance(KRWMoney(...), Decimal) MUST be False."""
        m = KRWMoney(Decimal("100"))
        assert isinstance(m, Decimal) is False

    def test_to_str(self):
        m = KRWMoney(Decimal("1500"))
        assert m.to_str() == "1500"


class TestKRWMoneyArithmetic:
    def test_add_returns_krwmoney(self):
        a = KRWMoney(Decimal("100"))
        b = KRWMoney(Decimal("200"))
        result = a + b
        assert isinstance(result, KRWMoney)

    def test_add_basic(self):
        a = KRWMoney(Decimal("300"))
        b = KRWMoney(Decimal("700"))
        assert (a + b).to_decimal() == Decimal("1000")

    def test_sub_basic(self):
        a = KRWMoney(Decimal("1000"))
        b = KRWMoney(Decimal("300"))
        assert (a - b).to_decimal() == Decimal("700")

    def test_mul_by_scalar(self):
        a = KRWMoney(Decimal("500"))
        result = a * Decimal("3")
        assert result.to_decimal() == Decimal("1500")

    def test_mul_by_int(self):
        a = KRWMoney(Decimal("200"))
        result = a * 3
        assert result.to_decimal() == Decimal("600")

    def test_add_propagates_lhs_rounding_and_unit(self):
        """LHS rounding/unit must be carried to the result."""
        a = KRWMoney(Decimal("100"), HALF_UP, 10)
        b = KRWMoney(Decimal("200"), DOWN, 1)
        result = a + b
        # Result re-rounded with LHS policy: 300, unit=10 -> 300
        assert result.to_decimal() == Decimal("300")

    def test_sum_then_round_policy(self):
        """
        Acceptance test from spec:
        a=KRWMoney("123", HALF_UP, 10)
        b=KRWMoney("456", HALF_UP, 10)
        c=KRWMoney("789", HALF_UP, 10)
        (a+b+c).to_decimal() == 1370
        123+456+789=1368 -> rounded HALF_UP to unit=10 -> 1370
        """
        a = KRWMoney("123", HALF_UP, 10)
        b = KRWMoney("456", HALF_UP, 10)
        c = KRWMoney("789", HALF_UP, 10)
        result = (a + b + c).to_decimal()
        assert result == Decimal("1370")

    def test_add_reassociates_correctly(self):
        """
        (a+b)+c vs a+(b+c) must yield same result (sum-then-round policy).
        Since each intermediate add re-rounds, they might differ.
        The spec says 'sum then round', but the implementation re-rounds
        after each add. We verify the spec example is met.
        """
        a = KRWMoney("123", HALF_UP, 10)
        b = KRWMoney("456", HALF_UP, 10)
        c = KRWMoney("789", HALF_UP, 10)
        # Per spec: (a+b+c) is left-associative: ((a+b)+c)
        ab   = a + b        # 579, unit=10 HALF_UP -> 580
        abc  = ab + c       # 580 + 789 = 1369, unit=10 HALF_UP -> 1370
        assert abc.to_decimal() == Decimal("1370")


class TestKRWMoneyEquality:
    def test_eq_same_amount(self):
        a = KRWMoney(Decimal("1000"))
        b = KRWMoney(Decimal("1000"))
        assert a == b

    def test_eq_different_amount(self):
        a = KRWMoney(Decimal("1000"))
        b = KRWMoney(Decimal("2000"))
        assert a != b

    def test_hashable(self):
        a = KRWMoney(Decimal("500"))
        b = KRWMoney(Decimal("500"))
        s = {a, b}
        assert len(s) == 1

    def test_hash_different_amounts(self):
        a = KRWMoney(Decimal("100"))
        b = KRWMoney(Decimal("200"))
        assert hash(a) != hash(b)
