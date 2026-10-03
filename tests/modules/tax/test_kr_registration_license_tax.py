"""Tests for tax.kr_registration_license_tax (부동산 등기 등록면허세).

기대값은 지방세법 제28조제1항제1호(정률 1천분의 2, 그 밖의 등기 건당 6천원, 같은 항 단서의 최저 세액)와
제151조제1항제2호(지방교육세 20%)를 조문대로 손으로 계산한 값이다. 끝수는 10원 미만 버림.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_registration_license_tax", **kwargs)


def money(result, key):
    return Decimal(result[key])


class TestRates:
    def test_mortgage_on_claim_amount(self):
        """저당권 채권금액 1억2천만 x 2/1000 = 240,000, 지방교육세 48,000."""
        r = call(registration_type="mortgage", tax_base="120000000", year=2026)
        assert money(r, "registration_tax") == 240000
        assert money(r, "local_education_tax") == 48000
        assert money(r, "total_tax") == 288000
        assert r["tax_base_kind"] == "채권금액"

    def test_jeonse(self):
        """전세권 전세금 3억 x 2/1000 = 600,000, 지방교육세 120,000."""
        r = call(registration_type="jeonse", tax_base="300000000", year=2026)
        assert money(r, "registration_tax") == 600000
        assert money(r, "total_tax") == 720000

    @pytest.mark.parametrize("kind", [
        "superficies", "servitude", "auction", "provisional_attachment",
        "provisional_disposition", "provisional_registration",
    ])
    def test_two_per_mille_types(self, kind):
        r = call(registration_type=kind, tax_base="50000000", year=2026)
        assert money(r, "rate") == Decimal("0.002")
        assert money(r, "registration_tax") == 100000

    def test_truncation_to_ten_won(self):
        """12,345,678 x 2/1000 = 24,691.356 -> 24,690. 교육세 4,938 -> 4,930."""
        r = call(registration_type="mortgage", tax_base="12345678", year=2026)
        assert money(r, "registration_tax") == 24690
        assert money(r, "local_education_tax") == 4930


class TestMinimumAndFlat:
    def test_lease_below_minimum_uses_6000(self):
        """임차권 월 임대차금액 100만 x 2/1000 = 2,000 < 6,000 -> 6,000 (제28조제1항 단서)."""
        r = call(registration_type="lease", tax_base="1000000", year=2026)
        assert r["minimum_applied"] is True
        assert money(r, "registration_tax") == 6000
        assert money(r, "local_education_tax") == 1200
        assert money(r, "total_tax") == 7200

    def test_exactly_minimum_is_not_flagged(self):
        """300만 x 2/1000 = 6,000 은 6천원보다 적지 않다."""
        r = call(registration_type="mortgage", tax_base="3000000", year=2026)
        assert r["minimum_applied"] is False
        assert money(r, "registration_tax") == 6000

    def test_other_registration_flat(self):
        """그 밖의 등기 건당 6천원 (제28조제1항제1호마목)."""
        r = call(registration_type="other", year=2026)
        assert money(r, "registration_tax") == 6000
        assert money(r, "total_tax") == 7200


class TestErrorsAndPolicy:
    @pytest.mark.parametrize("kwargs", [
        {"registration_type": "ownership_transfer", "tax_base": "100000000"},
        {"registration_type": "mortgage"},
        {"registration_type": "mortgage", "tax_base": "0"},
        {"registration_type": "mortgage", "tax_base": "-1000"},
    ])
    def test_invalid_inputs(self, kwargs):
        with pytest.raises(InvalidInputError):
            call(year=2026, **kwargs)

    def test_as_of_before_effective_date(self):
        with pytest.raises(PolicyNotInEffectError):
            call(registration_type="other", year=2026, as_of="2025-12-31")

    def test_policy_fields(self):
        r = call(registration_type="other", year=2026, as_of="2026-10-03")
        assert r["policy_status"] == "enacted"
        assert r["policy_effective_date"] == "2026-01-01"
