"""Tests for tax.capital_gains_kr tool.

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

기대값은 소득세법 제89조·제95조·제103조·제104조, 같은 법 시행령 제154조·제159조의4·제160조와
2026년 세제개편안(2027 개정안) 원문 수치로 계산했다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotEnactedError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


def call_capital_gains(**kwargs):
    return REGISTRY.invoke("tax.capital_gains_kr", **kwargs)


def land(**kwargs):
    """취득 1억원, 양도 2억원(양도차익 1억원) 주택 외 토지·건물."""
    args = {"acquisition_price": "100000000", "sale_price": "200000000", "is_one_house": False, "year": 2026}
    args.update(kwargs)
    return call_capital_gains(**args)


def house(**kwargs):
    """취득 3억원, 양도 4억원(양도차익 1억원) 주택."""
    args = {
        "acquisition_price": "300000000", "sale_price": "400000000", "is_one_house": False,
        "asset_type": "housing", "year": 2026,
    }
    args.update(kwargs)
    return call_capital_gains(**args)


class TestLongTermDeductionGeneral:
    def test_non_1house_5years(self):
        """일반 부동산, 5년 보유 → 표 1 10%."""
        result = land(holding_years=5)
        assert Decimal(result["gain"]) == Decimal("100000000")
        assert Decimal(result["ltct_deduction"]) == Decimal("10000000")
        assert Decimal(result["taxable_gain"]) == Decimal("90000000")

    def test_non_1house_3years(self):
        result = call_capital_gains(
            acquisition_price="200000000", sale_price="300000000",
            holding_years=3, is_one_house=False, year=2026,
        )
        assert Decimal(result["ltct_deduction"]) == Decimal(result["gain"]) * Decimal("0.06")

    def test_non_1house_2years_no_deduction(self):
        result = land(holding_years=2)
        assert result["ltct_deduction"] == "0"
        assert result["taxable_gain"] == result["gain"]

    def test_non_1house_15_and_20years_capped_at_30(self):
        for years in (15, 20):
            result = land(holding_years=years)
            assert Decimal(result["ltct_deduction"]) == Decimal(result["gain"]) * Decimal("0.30")


class TestBasicDeductionAndRates:
    def test_basic_deduction_and_basic_rate(self):
        """양도차익 1억, 5년 → 양도소득금액 9,000만, 기본공제 250만, 과세표준 8,750만.
        624만 + 3,750만 x 24% = 15,240,000."""
        result = land(holding_years=5)
        assert Decimal(result["basic_deduction"]) == Decimal("2500000")
        assert Decimal(result["tax_base"]) == Decimal("87500000")
        assert result["tax"] == "15240000"
        assert result["applied_rate"] == "basic"

    def test_basic_deduction_can_be_skipped(self):
        result = land(holding_years=5, apply_basic_deduction=False)
        assert result["basic_deduction"] == "0"
        assert Decimal(result["tax_base"]) == Decimal("90000000")

    def test_housing_under_1y_70pct(self):
        """주택 1년 미만: 과세표준 9,750만 x 70% = 68,250,000 (기본세율 18,685,000 보다 큼)."""
        result = house(holding_years=0)
        assert result["tax"] == "68250000"
        assert result["applied_rate"] == "short_term_under_1y"

    def test_housing_1_to_2y_60pct(self):
        assert house(holding_years=1)["tax"] == "58500000"

    def test_land_short_term_50_and_40pct(self):
        assert land(holding_years=0)["tax"] == "48750000"
        assert land(holding_years=1)["tax"] == "39000000"

    def test_non_business_land_plus_10pt(self):
        """비사업용 토지 과세표준 8,750만: 1,124만 + 3,750만 x 34% = 23,990,000."""
        result = land(holding_years=5, is_non_business_land=True)
        assert result["tax"] == "23990000"
        assert result["applied_rate"] == "non_business_land"

    def test_unregistered_70pct_without_deductions(self):
        result = land(holding_years=5, is_unregistered=True)
        assert result["ltct_deduction"] == "0"
        assert result["basic_deduction"] == "0"
        assert result["tax"] == "70000000"
        assert result["applied_rate"] == "unregistered"

    def test_presale_right_60_and_70pct(self):
        assert land(holding_years=3, asset_type="presale_right")["tax"] == "58500000"
        assert land(holding_years=3, asset_type="presale_right")["ltct_deduction"] == "0"
        assert land(holding_years=0, asset_type="presale_right")["tax"] == "68250000"


class TestOneHouse:
    def test_exempt_up_to_1_2b(self):
        """1세대1주택 양도가액 7억원(12억원 이하), 보유 10년 → 비과세."""
        result = call_capital_gains(
            acquisition_price="300000000", sale_price="700000000",
            holding_years=10, is_one_house=True, year=2026,
        )
        assert result["exempt"] is True
        assert result["tax"] == "0"
        assert result["taxable_gain"] == "0"

    def test_exactly_1_2b_is_exempt(self):
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1200000000",
            holding_years=3, is_one_house=True, year=2026,
        )
        assert result["exempt"] is True

    def test_high_value_house_allocation_full_residence(self):
        """양도 15억, 취득 5억, 보유·거주 10년: 과세 양도차익 10억 x 3억/15억 = 2억,
        장특 80% → 4,000만, 기본공제 후 3,750만 → 84만 + 2,350만 x 15% = 4,365,000."""
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1500000000",
            holding_years=10, residence_years=10, is_one_house=True, year=2026,
        )
        assert Decimal(result["taxable_portion_gain"]) == Decimal("200000000")
        assert Decimal(result["ltct_rate"]) == Decimal("0.80")
        assert Decimal(result["taxable_gain"]) == Decimal("40000000")
        assert result["tax"] == "4365000"

    def test_table_2_holding_and_residence_separately(self):
        """보유 15년(40%) + 거주 3년(12%) = 52%. 과세 양도차익 2억 → 9,600만, 과세표준 9,350만.
        1,536만 + 550만 x 35% = 17,285,000."""
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1500000000",
            holding_years=15, residence_years=3, is_one_house=True, year=2026,
        )
        assert Decimal(result["ltct_rate"]) == Decimal("0.52")
        assert result["tax"] == "17285000"

    def test_residence_2_years_rate_8pct(self):
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1500000000",
            holding_years=5, residence_years=2, is_one_house=True, year=2026,
        )
        assert Decimal(result["ltct_rate"]) == Decimal("0.20") + Decimal("0.08")

    def test_residence_under_2_years_uses_table_1(self):
        """거주 1년: 표 2 요건 미충족, 표 1 보유 10년 20%. 과세 양도차익 2억 → 1억6천만, 과세표준 1억5,750만.
        3,706만 + 750만 x 38% = 39,910,000."""
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1500000000",
            holding_years=10, residence_years=1, is_one_house=True, year=2026,
        )
        assert Decimal(result["ltct_rate"]) == Decimal("0.20")
        assert result["tax"] == "39910000"

    def test_regulated_area_acquisition_requires_residence(self):
        """취득 당시 조정대상지역, 거주 1년: 비과세 요건 미충족. 양도차익 3억, 표 1 10% → 2억7천만,
        과세표준 2억6,750만 → 3,706만 + 1억1,750만 x 38% = 81,710,000."""
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="800000000",
            holding_years=5, residence_years=1, acquired_in_regulated_area=True,
            is_one_house=True, year=2026,
        )
        assert result["exempt"] is False
        assert result["tax"] == "81710000"

    def test_holding_under_2_years_not_exempt(self):
        result = call_capital_gains(
            acquisition_price="300000000", sale_price="400000000",
            holding_years=1, is_one_house=True, year=2026,
        )
        assert result["exempt"] is False
        assert result["tax"] == "58500000"

    def test_residence_longer_than_holding_raises(self):
        with pytest.raises(InvalidInputError):
            call_capital_gains(
                acquisition_price="1", sale_price="2", holding_years=3, residence_years=4,
                is_one_house=True, year=2026,
            )


class TestMultiHouseSurcharge:
    def test_two_houses_after_exclusion_period(self):
        """조정대상지역 2주택, 2026.6.1. 양도: 장특 배제, 과세표준 9,750만에 기본세율 + 20%p = 38,185,000."""
        result = house(holding_years=5, multi_house_surcharge="two_houses", transfer_date="2026-06-01")
        assert result["ltct_deduction"] == "0"
        assert result["tax"] == "38185000"
        assert result["applied_rate"] == "multi_house_surcharge"

    def test_three_houses_plus_30pt(self):
        result = house(holding_years=5, multi_house_surcharge="three_plus", transfer_date="2026-06-01")
        assert result["tax"] == "47935000"

    def test_excluded_until_2026_05_09(self):
        """보유 2년 이상 주택을 2026.5.9.까지 양도하면 중과 제외: 표 1 10%, 15,240,000."""
        result = house(holding_years=5, multi_house_surcharge="two_houses", transfer_date="2026-05-09")
        assert Decimal(result["ltct_rate"]) == Decimal("0.10")
        assert result["tax"] == "15240000"

    def test_short_holding_takes_larger_of_surcharge_and_short_term(self):
        """보유 1년: 기본세율+20%p(38,185,000)와 60%(58,500,000) 중 큰 것."""
        result = house(holding_years=1, multi_house_surcharge="two_houses")
        assert result["tax"] == "58500000"

    def test_transfer_date_required_for_exclusion_check(self):
        with pytest.raises(InvalidInputError):
            house(holding_years=5, multi_house_surcharge="two_houses")

    def test_transfer_date_must_match_year(self):
        with pytest.raises(InvalidInputError):
            house(holding_years=5, multi_house_surcharge="two_houses", transfer_date="2025-12-31")

    def test_surcharge_with_one_house_raises(self):
        with pytest.raises(InvalidInputError):
            house(holding_years=5, is_one_house=True, multi_house_surcharge="two_houses")


class TestProposed2027:
    def test_requires_include_proposed(self):
        with pytest.raises(PolicyNotEnactedError):
            land(holding_years=5, year=2027)

    def test_surcharge_relief_two_houses(self):
        """개정안: 보유 2년 이상 2027년 양도 2주택 +5%p. 과세표준 9,750만 → 23,560,000."""
        result = house(
            holding_years=5, multi_house_surcharge="two_houses", year=2027, include_proposed=True,
        )
        assert result["policy_status"] == "proposed"
        assert result["tax"] == "23560000"

    def test_surcharge_relief_three_plus(self):
        """3주택 이상 +10%p → 28,435,000."""
        result = house(
            holding_years=5, multi_house_surcharge="three_plus", year=2027, include_proposed=True,
        )
        assert result["tax"] == "28435000"

    def test_long_residence_basic_deduction(self):
        """거주 10년, 양도 15억(30억 이하) 1세대1주택: 기본공제 2,500만. 양도소득금액 4,000만 → 과세표준 1,500만,
        84만 + 100만 x 15% = 990,000."""
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1500000000",
            holding_years=10, residence_years=10, is_one_house=True,
            year=2027, include_proposed=True,
        )
        assert Decimal(result["basic_deduction"]) == Decimal("25000000")
        assert result["tax"] == "990000"

    def test_long_residence_under_10_years_keeps_2_5m(self):
        result = call_capital_gains(
            acquisition_price="500000000", sale_price="1500000000",
            holding_years=10, residence_years=9, is_one_house=True,
            year=2027, include_proposed=True,
        )
        assert Decimal(result["basic_deduction"]) == Decimal("2500000")


class TestEdgeCases:
    def test_no_gain_returns_zero_tax(self):
        result = call_capital_gains(
            acquisition_price="200000000", sale_price="200000000",
            holding_years=5, is_one_house=False, year=2026,
        )
        assert result["tax"] == "0"
        assert result["gain"] == "0"

    def test_loss_returns_zero_tax(self):
        result = call_capital_gains(
            acquisition_price="200000000", sale_price="100000000",
            holding_years=5, is_one_house=False, year=2026,
        )
        assert result["tax"] == "0"

    def test_negative_acquisition_raises(self):
        with pytest.raises(InvalidInputError):
            land(acquisition_price="-1", holding_years=5)

    def test_invalid_asset_type_raises(self):
        with pytest.raises(InvalidInputError):
            land(holding_years=5, asset_type="stock")

    def test_non_business_land_requires_land(self):
        with pytest.raises(InvalidInputError):
            house(holding_years=5, is_non_business_land=True)

    def test_unsupported_year_raises(self):
        with pytest.raises(UnsupportedPolicyError):
            land(holding_years=5, year=2099)

    def test_policy_version_returned(self):
        pv = land(holding_years=5)["policy_version"]
        assert pv["year"] == 2026
