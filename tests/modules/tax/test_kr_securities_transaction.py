"""Tests for tax.kr_securities_transaction (증권거래세, 농어촌특별세).

기대값은 증권거래세법 제8조, 같은 법 시행령 제5조(2022-12-31 개정본과 2025-12-31 개정본),
농어촌특별세법 제5조제1항제5호의 세율을 양도가액에 곱해 원 미만을 버린 값이다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotInEffectError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_securities_transaction", **kwargs)


class TestRates2026:
    def test_kospi_effective_020_percent(self):
        """유가증권시장 1천만원: 증권거래세 0.05% 5,000 + 농특세 0.15% 15,000 = 20,000."""
        r = call(transfer_amount="10000000", market="kospi", year=2026)
        assert Decimal(r["securities_tax"]) == Decimal("5000")
        assert Decimal(r["rural_special_tax"]) == Decimal("15000")
        assert Decimal(r["total_tax"]) == Decimal("20000")
        assert Decimal(r["effective_rate"]) == Decimal("0.0020")
        assert r["rate_basis"] == "elastic"

    def test_kosdaq_020_percent_without_rural_tax(self):
        """코스닥 1천만원: 0.20% 20,000, 농특세 없음 (농특세법 시행령 제5조제1항은 유가증권시장만)."""
        r = call(transfer_amount="10000000", market="kosdaq", year=2026)
        assert Decimal(r["securities_tax"]) == Decimal("20000")
        assert Decimal(r["rural_special_tax"]) == Decimal("0")
        assert Decimal(r["total_tax"]) == Decimal("20000")

    def test_konex_010_percent(self):
        """코넥스 1천만원: 0.10% 10,000 (시행령 제5조제2호)."""
        r = call(transfer_amount="10000000", market="konex", year=2026)
        assert Decimal(r["total_tax"]) == Decimal("10000")

    def test_k_otc_020_percent(self):
        """금융투자협회 장외(K-OTC) 1천만원: 0.20% 20,000 (시행령 제5조제3호나목)."""
        r = call(transfer_amount="10000000", market="k_otc", year=2026)
        assert Decimal(r["total_tax"]) == Decimal("20000")

    def test_other_statutory_035_percent(self):
        """그 밖의 장외·비상장 1천만원: 기본세율 0.35% 35,000 (법 제8조제1항)."""
        r = call(transfer_amount="10000000", market="other", year=2026)
        assert Decimal(r["securities_tax"]) == Decimal("35000")
        assert Decimal(r["rural_special_tax"]) == Decimal("0")
        assert r["rate_basis"] == "statutory"

    def test_truncates_below_one_won(self):
        """1,234,567원 × 0.05% = 617.2835 → 617, × 0.15% = 1,851.8505 → 1,851."""
        r = call(transfer_amount="1234567", market="kospi", year=2026)
        assert Decimal(r["securities_tax"]) == Decimal("617")
        assert Decimal(r["rural_special_tax"]) == Decimal("1851")
        assert Decimal(r["total_tax"]) == Decimal("2468")

    def test_zero_amount(self):
        r = call(transfer_amount="0", market="kospi", year=2026)
        assert Decimal(r["total_tax"]) == Decimal("0")

    def test_policy_fields_present(self):
        r = call(transfer_amount="10000000", market="kospi", year=2026)
        assert r["policy_status"] == "enacted"
        assert r["policy_effective_date"] == "2026-01-01"
        assert any(c["law"] == "증권거래세법 시행령" for c in r["policy_citations"])


class TestRatesByTransferYear:
    def test_2025_kospi_zero_rate_keeps_rural_tax(self):
        """2025 유가증권시장 영의 세율: 증권거래세 0, 농특세 15,000 (농특세법 제4조제7호 단서)."""
        r = call(transfer_amount="10000000", market="kospi", year=2025)
        assert Decimal(r["securities_tax"]) == Decimal("0")
        assert Decimal(r["rural_special_tax"]) == Decimal("15000")
        assert Decimal(r["effective_rate"]) == Decimal("0.0015")

    def test_2025_kosdaq_015_percent(self):
        r = call(transfer_amount="10000000", market="kosdaq", year=2025)
        assert Decimal(r["total_tax"]) == Decimal("15000")

    def test_2024_kospi_003_percent(self):
        """2024 유가증권시장 1만분의 3: 3,000 + 농특세 15,000."""
        r = call(transfer_amount="10000000", market="kospi", year=2024)
        assert Decimal(r["securities_tax"]) == Decimal("3000")
        assert Decimal(r["total_tax"]) == Decimal("18000")

    def test_2024_kosdaq_018_percent(self):
        r = call(transfer_amount="10000000", market="kosdaq", year=2024)
        assert Decimal(r["total_tax"]) == Decimal("18000")

    def test_2023_kosdaq_020_percent(self):
        r = call(transfer_amount="10000000", market="kosdaq", year=2023)
        assert Decimal(r["total_tax"]) == Decimal("20000")


class TestAsOf:
    def test_2026_policy_not_in_effect_before_start(self):
        with pytest.raises(PolicyNotInEffectError):
            call(transfer_amount="10000000", market="kospi", year=2026, as_of="2025-12-31")

    def test_2026_policy_in_effect_on_start(self):
        r = call(transfer_amount="10000000", market="kospi", year=2026, as_of="2026-01-01")
        assert Decimal(r["securities_tax"]) == Decimal("5000")

    def test_2025_policy_ends_on_dec_31(self):
        r = call(transfer_amount="10000000", market="kospi", year=2025, as_of="2025-12-31")
        assert Decimal(r["securities_tax"]) == Decimal("0")
        with pytest.raises(PolicyNotInEffectError):
            call(transfer_amount="10000000", market="kospi", year=2025, as_of="2026-01-01")


class TestErrors:
    def test_negative_amount(self):
        with pytest.raises(InvalidInputError):
            call(transfer_amount="-1", market="kospi", year=2026)

    def test_unknown_market(self):
        with pytest.raises(InvalidInputError):
            call(transfer_amount="10000000", market="nasdaq", year=2026)

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call(transfer_amount="10000000", market="kospi", year=2022)
