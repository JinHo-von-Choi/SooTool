"""Tests for tax.kr_gift.

기대값은 상속세 및 증여세법 제26조 세율표, 제53조·제53조의2 공제액, 제57조 할증률,
제69조제2항 신고세액공제율로 직접 계산한 값이다.
"""
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
        """직계비속으로부터 1억 증여: 공제 5000만 → 과세 5000만; 10% = 500만."""
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


class TestKrGiftLookback:
    def test_prior_deduction_reduces_limit(self):
        """직계존속 1억, 10년 내 기공제 3천만 → 공제 2천만, 과세 8천만, 세액 800만."""
        r = call(
            gift_amount="100000000", relationship="lineal_ascendant", year=2026,
            prior_deduction_used_10y="30000000",
        )
        assert Decimal(r["deduction"]) == Decimal("20000000")
        assert Decimal(r["taxable_base"]) == Decimal("80000000")
        assert Decimal(r["tax"]) == Decimal("8000000")

    def test_prior_deduction_exhausted(self):
        """기공제 6천만(한도 5천만 초과) → 공제 0, 1억 x 10% = 1,000만."""
        r = call(
            gift_amount="100000000", relationship="lineal_ascendant", year=2026,
            prior_deduction_used_10y="60000000",
        )
        assert Decimal(r["deduction"]) == Decimal("0")
        assert Decimal(r["tax"]) == Decimal("10000000")

    def test_negative_prior_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                gift_amount="100000000", relationship="lineal_ascendant", year=2026,
                prior_deduction_used_10y="-1",
            )


class TestKrGiftMarriageBirth:
    def test_marriage_deduction_covers_gift(self):
        """혼인 증여 1.5억: 5천만 + 1억 공제 → 과세 0."""
        r = call(
            gift_amount="150000000", relationship="lineal_ascendant", year=2026,
            marriage_birth_gift=True,
        )
        assert Decimal(r["deduction"]) == Decimal("50000000")
        assert Decimal(r["marriage_birth_deduction"]) == Decimal("100000000")
        assert Decimal(r["taxable_base"]) == Decimal("0")
        assert Decimal(r["tax"]) == Decimal("0")

    def test_marriage_deduction_3억(self):
        """혼인 증여 3억: 과세 1.5억 → 1천만 + 5천만 x 20% = 2,000만."""
        r = call(
            gift_amount="300000000", relationship="lineal_ascendant", year=2026,
            marriage_birth_gift=True,
        )
        assert Decimal(r["taxable_base"]) == Decimal("150000000")
        assert Decimal(r["tax"]) == Decimal("20000000")

    def test_marriage_birth_lifetime_limit(self):
        """출산 증여, 혼인 공제 기사용 4천만 → 잔여 6천만. 과세 1.9억 → 1천만 + 9천만 x 20% = 2,800만."""
        r = call(
            gift_amount="300000000", relationship="lineal_ascendant", year=2026,
            marriage_birth_gift=True, prior_marriage_birth_deduction="40000000",
        )
        assert Decimal(r["marriage_birth_deduction"]) == Decimal("60000000")
        assert Decimal(r["tax"]) == Decimal("28000000")

    def test_marriage_birth_requires_ascendant(self):
        with pytest.raises(InvalidInputError):
            call(
                gift_amount="300000000", relationship="spouse", year=2026,
                marriage_birth_gift=True,
            )


class TestKrGiftSurchargeAndFilingCredit:
    def test_generation_skip_30pct(self):
        """조부모 → 성년 손자녀 3억: 과세 2.5억 → 산출 4,000만, 할증 30% 1,200만, 합계 5,200만."""
        r = call(
            gift_amount="300000000", relationship="lineal_ascendant", year=2026,
            generation_skip=True,
        )
        assert Decimal(r["computed_tax"]) == Decimal("40000000")
        assert Decimal(r["generation_skip_surcharge"]) == Decimal("12000000")
        assert Decimal(r["tax"]) == Decimal("52000000")
        assert Decimal(r["filing_credit"]) == Decimal("1560000")
        assert Decimal(r["tax_after_filing_credit"]) == Decimal("50440000")

    def test_generation_skip_minor_over_20억_40pct(self):
        """미성년 손자녀 25억: 과세 24.8억 → 2.4억 + 14.8억 x 40% = 8.32억, 할증 40% 3.328억."""
        r = call(
            gift_amount="2500000000", relationship="lineal_ascendant_minor", year=2026,
            generation_skip=True,
        )
        assert Decimal(r["computed_tax"]) == Decimal("832000000")
        assert Decimal(r["generation_skip_surcharge"]) == Decimal("332800000")
        assert Decimal(r["tax"]) == Decimal("1164800000")

    def test_generation_skip_minor_at_20억_30pct(self):
        """미성년 손자녀 20억(초과 아님): 과세 19.8억 → 6.32억, 할증 30% 1.896억."""
        r = call(
            gift_amount="2000000000", relationship="lineal_ascendant_minor", year=2026,
            generation_skip=True,
        )
        assert Decimal(r["computed_tax"]) == Decimal("632000000")
        assert Decimal(r["generation_skip_surcharge"]) == Decimal("189600000")

    def test_generation_skip_requires_ascendant(self):
        with pytest.raises(InvalidInputError):
            call(
                gift_amount="300000000", relationship="spouse", year=2026,
                generation_skip=True,
            )

    def test_filing_credit_3pct(self):
        """배우자 10억: 산출 7,000만, 신고세액공제 210만 → 6,790만."""
        r = call(gift_amount="1000000000", relationship="spouse", year=2026)
        assert Decimal(r["filing_credit"]) == Decimal("2100000")
        assert Decimal(r["tax_after_filing_credit"]) == Decimal("67900000")

    def test_no_filing_credit_when_not_filed(self):
        r = call(
            gift_amount="1000000000", relationship="spouse", year=2026,
            timely_filing=False,
        )
        assert Decimal(r["filing_credit"]) == Decimal("0")
        assert Decimal(r["tax_after_filing_credit"]) == Decimal("70000000")
