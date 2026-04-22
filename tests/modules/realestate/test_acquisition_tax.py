"""Tests for Korean acquisition tax calculator."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestAcquisitionTax:
    def test_acquisition_tax_6억_first_house(self) -> None:
        """6억원 1주택 취득 -> 1% 기본세 + 지방교육세 0.1% = 660만원."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="600000000",
            house_count=1,
            is_regulated=False,
            area_m2="84",
            year=2026,
        )
        base_tax  = Decimal(result["base_tax"])
        total_tax = Decimal(result["total_tax"])
        # 기본세 1% = 6,000,000
        assert base_tax == Decimal("6000000")
        # 지방교육세 0.1% = 600,000 -> total = 6,600,000
        # (면적 84m² <= 85 -> 농특세 없음)
        assert total_tax == Decimal("6600000")
        assert "surcharges" in result
        assert "trace" in result

    def test_acquisition_tax_10억_first_house(self) -> None:
        """10억원 1주택 -> 3% bracket."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="1000000000",
            house_count=1,
            is_regulated=False,
            area_m2="60",
            year=2026,
        )
        base_tax = Decimal(result["base_tax"])
        # 3% of 10억 = 30,000,000
        assert base_tax == Decimal("30000000")

    def test_acquisition_tax_multi_house_surcharge_3plus(self) -> None:
        """3주택 이상 취득 -> 12% 중과세."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="500000000",
            house_count=3,
            is_regulated=True,
            area_m2="60",
            year=2026,
        )
        surcharge = Decimal(result["surcharges"]["multi_house_surcharge"])
        # 12% of 5억 = 60,000,000
        assert surcharge == Decimal("60000000")

    def test_acquisition_tax_2house_regulated_surcharge(self) -> None:
        """2주택, 규제지역 -> 8% 중과세."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="500000000",
            house_count=2,
            is_regulated=True,
            area_m2="60",
            year=2026,
        )
        surcharge = Decimal(result["surcharges"]["multi_house_surcharge"])
        # 8% of 5억 = 40,000,000
        assert surcharge == Decimal("40000000")

    def test_acquisition_tax_2house_non_regulated_no_surcharge(self) -> None:
        """2주택, 비규제지역 -> 중과세 0."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="500000000",
            house_count=2,
            is_regulated=False,
            area_m2="60",
            year=2026,
        )
        surcharge = Decimal(result["surcharges"]["multi_house_surcharge"])
        assert surcharge == Decimal("0")

    def test_acquisition_tax_rural_special_large_area(self) -> None:
        """전용면적 85m² 초과 -> 농어촌특별세 0.2% 부과."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="600000000",
            house_count=1,
            is_regulated=False,
            area_m2="100",
            year=2026,
        )
        rural = Decimal(result["surcharges"]["rural_special"])
        # 0.2% of 6억 = 1,200,000
        assert rural == Decimal("1200000")

    def test_acquisition_tax_rural_special_small_area(self) -> None:
        """전용면적 85m² 이하 -> 농어촌특별세 없음."""
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="600000000",
            house_count=1,
            is_regulated=False,
            area_m2="85",
            year=2026,
        )
        rural = Decimal(result["surcharges"]["rural_special"])
        assert rural == Decimal("0")

    def test_acquisition_tax_policy_version(self) -> None:
        result = REGISTRY.invoke(
            "realestate.kr_acquisition_tax",
            price="600000000",
            house_count=1,
            is_regulated=False,
            area_m2="60",
            year=2026,
        )
        pv = result["policy_version"]
        assert pv["year"] == 2026

    def test_acquisition_tax_zero_price_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.kr_acquisition_tax",
                price="0",
                house_count=1,
                is_regulated=False,
                area_m2="60",
                year=2026,
            )
