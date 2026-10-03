"""Tests for tax.kr_simplified_vat (간이과세자 부가가치세)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError, PolicyNotEnactedError
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
        """세금계산서등 수취 공급대가 × 0.5% 공제 (법 제63조제3항제1호)."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            input_tax_amount="20000000",
        )
        # vat_payable: 8천만 × 15% × 10% = 120만
        # input_credit: 2천만 × 0.5% = 10만
        # net: 110만
        assert Decimal(r["input_credit"]) == Decimal("100000")
        assert Decimal(r["net_payable"]) == Decimal("1100000")

    def test_input_credit_does_not_depend_on_business_type(self):
        """공제율은 업종과 무관하게 0.5%: 제조업 2천만 수취 → 10만."""
        r = call(
            supply_value="80000000",
            business_type="manufacturing",
            year=2026,
            input_tax_amount="20000000",
        )
        assert Decimal(r["input_credit"]) == Decimal("100000")
        assert Decimal(r["net_payable"]) == Decimal("1500000")

    def test_input_credit_exceeds_payable(self):
        """공제세액이 납부세액을 초과해도 net은 0 (법 제63조제6항)."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            input_tax_amount="300000000",
        )
        # input_credit: 3억 × 0.5% = 150만. vat_payable 120만 → net 0
        assert Decimal(r["input_credit"]) == Decimal("1500000")
        assert Decimal(r["net_payable"]) == Decimal("0")

    def test_card_sales_credit(self):
        """신용카드 매출 5천만 × 1.3% = 65만 공제 (법 제46조제1항제3호, 2026-12-31까지)."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            card_sales_amount="50000000",
        )
        assert Decimal(r["card_sales_credit"]) == Decimal("650000")
        assert Decimal(r["net_payable"]) == Decimal("550000")

    def test_card_sales_credit_annual_limit(self):
        """카드 매출 10억 × 1.3% = 1,300만 → 연간 한도 1,000만. 공제 합계 초과분은 없음."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            card_sales_amount="1000000000",
        )
        assert Decimal(r["card_sales_credit"]) == Decimal("10000000")
        assert Decimal(r["net_payable"]) == Decimal("0")

    def test_combined_credits(self):
        """수취분 10만 + 카드 65만 = 75만 공제 → 120만 - 75만 = 45만."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            input_tax_amount="20000000",
            card_sales_amount="50000000",
        )
        assert Decimal(r["net_payable"]) == Decimal("450000")

    def test_threshold_exceeded_flag(self):
        """1억 4백만 이상 공급대가 → threshold_exceeded=True."""
        r = call(supply_value="105000000", business_type="retail", year=2026)
        assert r["threshold_exceeded"] is True
        assert r["threshold_basis"] == "supply_value"

    def test_threshold_uses_prior_year_supply(self):
        """간이과세 기준은 직전 연도 공급대가 (법 제61조제1항)."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2026,
            prior_year_supply="104000000",
        )
        assert r["threshold_exceeded"] is True
        assert r["threshold_basis"] == "prior_year_supply"
        r = call(
            supply_value="110000000",
            business_type="retail",
            year=2026,
            prior_year_supply="103999999",
        )
        assert r["threshold_exceeded"] is False

    def test_real_estate_rental_restricted_threshold(self):
        """부동산임대업: 직전 연도 공급대가 4,800만원 이상이면 간이과세 배제 (법 제61조제1항제3호)."""
        r = call(
            supply_value="50000000",
            business_type="real_estate_rental",
            year=2026,
            prior_year_supply="48000000",
        )
        assert Decimal(r["value_added_rate"]) == Decimal("0.40")
        assert Decimal(r["applicable_threshold"]) == Decimal("48000000")
        assert r["threshold_exceeded"] is True

    def test_restricted_business_flag(self):
        """과세유흥장소 경영자: restricted_business=True 로 4,800만원 기준 적용."""
        r = call(
            supply_value="50000000",
            business_type="retail",
            year=2026,
            prior_year_supply="50000000",
            restricted_business=True,
        )
        assert r["threshold_exceeded"] is True
        r = call(
            supply_value="50000000",
            business_type="retail",
            year=2026,
            prior_year_supply="50000000",
        )
        assert r["threshold_exceeded"] is False


class TestSimplifiedVat2027Proposed:
    def test_2027_requires_include_proposed(self):
        with pytest.raises(PolicyNotEnactedError):
            call(supply_value="80000000", business_type="retail", year=2027)

    def test_2027_proposed_card_credit(self):
        """2026 세제개편안: 2027-01-01 이후 공급분 1.2%, 연 500만원. 5천만 × 1.2% = 60만."""
        r = call(
            supply_value="80000000",
            business_type="retail",
            year=2027,
            card_sales_amount="50000000",
            include_proposed=True,
        )
        assert r["policy_status"] == "proposed"
        assert Decimal(r["card_sales_credit"]) == Decimal("600000")
        assert Decimal(r["net_payable"]) == Decimal("600000")

    def test_2027_proposed_card_limit(self):
        """카드 매출 10억 × 1.2% = 1,200만 → 연 500만 한도."""
        r = call(
            supply_value="200000000",
            business_type="retail",
            year=2027,
            card_sales_amount="1000000000",
            include_proposed=True,
        )
        assert Decimal(r["card_sales_credit"]) == Decimal("5000000")


class TestSimplifiedVatValidation:
    def test_invalid_business_type_raises(self):
        with pytest.raises(InvalidInputError):
            call(supply_value="50000000", business_type="unknown", year=2026)

    def test_negative_supply_raises(self):
        with pytest.raises(InvalidInputError):
            call(supply_value="-1", business_type="retail", year=2026)

    def test_negative_card_sales_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                supply_value="80000000",
                business_type="retail",
                year=2026,
                card_sales_amount="-1",
            )

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
