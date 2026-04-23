"""Tests for tax.kr_gift."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_gift", **kwargs)


class TestKrGift:
    def test_spouse_6억_deduction(self):
        """배우자 10억 증여: 공제 6억 → 과세 4억; 1억*10% + 3억*20% = 70M."""
        r = call(gift_amount="1000000000", relationship="spouse", year=2026)
        assert Decimal(r["deduction"]) == Decimal("600000000")
        assert Decimal(r["taxable_base"]) == Decimal("400000000")
        expected = Decimal("100000000") * Decimal("0.10") + Decimal("300000000") * Decimal("0.20")
        assert Decimal(r["tax"]) == expected.quantize(Decimal("1"))

    def test_lineal_descendant_5천만(self):
        r = call(gift_amount="50000000", relationship="lineal_descendant", year=2026)
        assert Decimal(r["taxable_base"]) == Decimal("0")
        assert Decimal(r["tax"]) == Decimal("0")

    def test_lineal_descendant_1억(self):
        """성인 직계비속 1억 증여: 공제 5000만 → 과세 5000만; 10% = 500만."""
        r = call(gift_amount="100000000", relationship="lineal_descendant", year=2026)
        assert Decimal(r["deduction"]) == Decimal("50000000")
        assert Decimal(r["tax"]) == Decimal("5000000")

    def test_minor_ascendant_limited(self):
        r = call(gift_amount="30000000", relationship="lineal_ascendant_minor", year=2026)
        assert Decimal(r["deduction"]) == Decimal("20000000")
        assert Decimal(r["taxable_base"]) == Decimal("10000000")

    def test_other_relative(self):
        r = call(gift_amount="20000000", relationship="other_relative", year=2026)
        assert Decimal(r["deduction"]) == Decimal("10000000")

    def test_other_no_deduction(self):
        r = call(gift_amount="10000000", relationship="other", year=2026)
        assert Decimal(r["deduction"]) == Decimal("0")

    def test_invalid_relationship_raises(self):
        with pytest.raises(InvalidInputError):
            call(gift_amount="100000000", relationship="enemy", year=2026)

    def test_negative_raises(self):
        with pytest.raises(InvalidInputError):
            call(gift_amount="-1", relationship="spouse", year=2026)

    def test_trace_present(self):
        r = call(gift_amount="100000000", relationship="spouse", year=2026)
        assert r["trace"]["tool"] == "tax.kr_gift"
