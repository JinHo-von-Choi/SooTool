"""Tests for tax.kr_simplified_vat (간이과세자 부가가치세)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("tax.kr_simplified_vat", **kwargs)


class TestSimplifiedVatBasic:
    def test_retail_standard(self):
        """소매업 8천만: 8천만 × 15% × 10% = 120만."""
        r = call(supply_value="80000000", business_type="retail", year=2026)
        assert Decimal(r["value_added_rate"]) == Decimal("0.15")
        assert Decimal(r["vat_payable"]) == Decimal("1200000")
        assert Decimal(r["net_payable"]) == Decimal("1200000")
        assert r["threshold_exceeded"] is False
        assert r["nonpayment_exempt"] is False

    def test_manufacturing_20_percent(self):
        """제조업 8천만: 8천만 × 20% × 10% = 160만."""
        r = call(supply_value="80000000", business_type="manufacturing", year=2026)
        assert Decimal(r["value_added_rate"]) == Decimal("0.20")
        assert Decimal(r["vat_payable"]) == Decimal("1600000")
        assert Decimal(r["net_payable"]) == Decimal("1600000")

    def test_financial_40_percent(self):
        """금융·보험 5천만: 5천만 × 40% × 10% = 200만."""
        r = call(supply_value="50000000", business_type="financial", year=2026)
        assert Decimal(r["value_added_rate"]) == Decimal("0.40")
        assert Decimal(r["vat_payable"]) == Decimal("2000000")

    def test_accommodation_25_percent(self):
        r = call(supply_value="60000000", business_type="accommodation", year=2026)
        assert Decimal(r["value_added_rate"]) == Decimal("0.25")
        # 60000000 * 0.25 * 0.10 = 1500000
        assert Decimal(r["vat_payable"]) == Decimal("1500000")

    def test_construction_30_percent(self):
        r = call(supply_value="80000000", business_type="construction", year=2026)
        assert Decimal(r["value_added_rate"]) == Decimal("0.30")
        assert Decimal(r["vat_payable"]) == Decimal("2400000")


class TestSimplifiedVatExemptionAndCredit:
    def test_nonpayment_exemption_below_48m(self):
        """4,700만 공급대가 → 납부면제 (4,800만 미만)."""
        r = call(supply_value="47000000", business_type="retail", year=2026)
        assert r["nonpayment_exempt"] is True
        assert Decimal(r["net_payable"]) == Decimal("0")
        # vat_payable은 계산되지만 net만 0
        assert Decimal(r["vat_payable"]) > Decimal("0")

    def test_input_credit_subtraction(self):
        """매입공제세액 차감."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            input_tax_amount="20000000",
        )
        # vat_payable: 8천만 × 15% × 10% = 120만
        # input_credit: 2천만 × 15% × 10% = 30만
        # net: 90만
        assert Decimal(r["input_credit"]) == Decimal("300000")
        assert Decimal(r["net_payable"]) == Decimal("900000")

    def test_input_credit_exceeds_payable(self):
        """공제세액이 납부세액을 초과해도 net은 0 (환급 없음)."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            input_tax_amount="100000000",
        )
        # input_credit: 1억 × 15% × 10% = 150만. vat_payable 120만 → net 0
        assert Decimal(r["net_payable"]) == Decimal("0")

    def test_threshold_exceeded_flag(self):
        """1억 4백만 이상 공급대가 → threshold_exceeded=True."""
        r = call(supply_value="105000000", business_type="retail", year=2026)
        assert r["threshold_exceeded"] is True


class TestSimplifiedVatValidation:
    def test_invalid_business_type_raises(self):
        with pytest.raises(InvalidInputError):
            call(supply_value="50000000", business_type="unknown", year=2026)

    def test_negative_supply_raises(self):
        with pytest.raises(InvalidInputError):
            call(supply_value="-1", business_type="retail", year=2026)

    def test_negative_input_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                supply_value="80000000",
                business_type="retail",
                year=2026,
                input_tax_amount="-1",
            )

    def test_trace_and_policy_version(self):
        r = call(supply_value="80000000", business_type="retail", year=2026)
        assert r["trace"]["tool"] == "tax.kr_simplified_vat"
        assert "formula" in r["trace"]
        assert r["policy_version"]["year"] == 2026
        assert r["policy_sha256"] != ""
        assert "policy_source" in r


class TestSimplifiedVatBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"svat-{i}",
                "tool": "tax.kr_simplified_vat",
                "args": {
                    "supply_value":  "80000000",
                    "business_type": "retail",
                    "year":          2026,
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        for r in response["results"]:
            assert r["result"]["vat_payable"] == "1200000"
            assert r["result"]["net_payable"] == "1200000"
