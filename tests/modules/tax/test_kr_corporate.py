"""Tests for tax.kr_corporate."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_corporate", **kwargs)


class TestKrCorporate:
    def test_2억_boundary_9pct(self):
        """과세표준 2억원: 전액 9% = 18,000,000"""
        r = call(taxable_income="200000000", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("18000000")

    def test_500억_spans_3_brackets(self):
        """500억원 = 2억*9% + 198억*19% + 298억*21% = 18M + 3,762M + 6,258M = 10,038M"""
        r = call(taxable_income="50000000000", year=2026)
        expected = Decimal("200000000") * Decimal("0.09") \
                 + (Decimal("20000000000") - Decimal("200000000")) * Decimal("0.19") \
                 + (Decimal("50000000000") - Decimal("20000000000")) * Decimal("0.21")
        assert Decimal(r["base_tax"]) == expected.quantize(Decimal("1"))

    def test_zero_income(self):
        r = call(taxable_income="0", year=2026)
        assert Decimal(r["base_tax"]) == Decimal("0")

    def test_small_firm_minimum_tax_floor(self):
        """중소기업 최저한세 7%가 기본 세액보다 높으면 최저한세 적용."""
        # 과세표준 1억: 일반 세율 9% = 900만
        # 중소 최저한세 7% = 700만 → 기본이 크므로 base 그대로
        r = call(taxable_income="100000000", year=2026, is_small=True)
        assert Decimal(r["base_tax"]) >= Decimal(r["minimum_tax"])
        assert Decimal(r["tax"]) == Decimal(r["base_tax"])

    def test_negative_income_raises(self):
        with pytest.raises(InvalidInputError):
            call(taxable_income="-1", year=2026)

    def test_unsupported_year_raises(self):
        with pytest.raises(UnsupportedPolicyError):
            call(taxable_income="100000000", year=2099)

    def test_policy_version_exposed(self):
        r = call(taxable_income="100000000", year=2026)
        pv = r["policy_version"]
        assert pv["year"] == 2026
        assert "sha256" in pv

    def test_trace_present(self):
        r = call(taxable_income="100000000", year=2026)
        assert "trace" in r
        assert r["trace"]["tool"] == "tax.kr_corporate"
