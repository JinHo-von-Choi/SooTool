"""Tests for Korean acquisition tax calculator.

기대값은 지방세법 제11조제1항제8호(표준세율), 제13조의2(중과세율), 제151조제1항제1호(지방교육세),
농어촌특별세법 제5조제1항제6호에서 직접 계산한 값이다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("realestate.kr_acquisition_tax", **kwargs)


class TestAcquisitionTax:
    def test_acquisition_tax_6억_first_house(self) -> None:
        """6억원 1주택 취득 -> 1% 기본세 + 지방교육세 0.1% = 660만원."""
        result = call(price="600000000", house_count=1, is_regulated=False, area_m2="84", year=2026)
        assert Decimal(result["base_tax"]) == Decimal("6000000")
        # 지방교육세 = 1% × 10% = 0.1% -> 60만원, 84m² 이하 농특세 없음
        assert Decimal(result["surcharges"]["local_edu"]) == Decimal("600000")
        assert Decimal(result["total_tax"]) == Decimal("6600000")
        assert "trace" in result

    def test_acquisition_tax_10억_first_house(self) -> None:
        """10억원 1주택 -> 3%, 지방교육세 3% × 10% = 0.3%."""
        result = call(price="1000000000", house_count=1, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["base_tax"]) == Decimal("30000000")
        assert Decimal(result["surcharges"]["local_edu"]) == Decimal("3000000")
        assert Decimal(result["total_tax"]) == Decimal("33000000")

    def test_6억_초과_9억_이하_산식_7억(self) -> None:
        """7억: (7억 × 2/3억 - 3)/100 = 0.016666... -> 넷째자리 반올림 0.0167.

        취득세 = 7억 × 1.67% = 1,169만원, 지방교육세 = 7억 × 0.167% = 116.9만원.
        """
        result = call(price="700000000", house_count=1, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["standard_rate"]) == Decimal("0.0167")
        assert Decimal(result["base_tax"]) == Decimal("11690000")
        assert Decimal(result["surcharges"]["local_edu"]) == Decimal("1169000")
        assert Decimal(result["total_tax"]) == Decimal("12859000")

    def test_6억_초과_9억_이하_산식_8억(self) -> None:
        """8억: (8 × 2/3 - 3)/100 = 0.023333... -> 0.0233, 취득세 1,864만원."""
        result = call(price="800000000", house_count=1, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["standard_rate"]) == Decimal("0.0233")
        assert Decimal(result["base_tax"]) == Decimal("18640000")

    def test_6억_초과_9억_이하_산식_7억5천(self) -> None:
        """7.5억: (7.5 × 2/3 - 3)/100 = 0.02 정확히."""
        result = call(price="750000000", house_count=1, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["standard_rate"]) == Decimal("0.02")
        assert Decimal(result["base_tax"]) == Decimal("15000000")

    def test_acquisition_tax_multi_house_surcharge_3plus(self) -> None:
        """조정 3주택 5억 -> 12%가 표준세율을 대체: 취득세 6천만원.

        표준세율분 500만원 + 중과 증가분 5,500만원, 지방교육세 0.4% = 200만원.
        """
        result = call(price="500000000", house_count=3, is_regulated=True, area_m2="60", year=2026)
        assert Decimal(result["acquisition_tax"]) == Decimal("60000000")
        assert Decimal(result["base_tax"]) == Decimal("5000000")
        assert Decimal(result["surcharges"]["multi_house_surcharge"]) == Decimal("55000000")
        assert Decimal(result["surcharges"]["local_edu"]) == Decimal("2000000")
        assert Decimal(result["surcharges"]["rural_special"]) == Decimal("0")
        assert Decimal(result["total_tax"]) == Decimal("62000000")

    def test_acquisition_tax_2house_regulated_surcharge(self) -> None:
        """조정 2주택 5억 -> 8%: 취득세 4천만원, 지방교육세 200만원."""
        result = call(price="500000000", house_count=2, is_regulated=True, area_m2="60", year=2026)
        assert Decimal(result["acquisition_tax"]) == Decimal("40000000")
        assert Decimal(result["surcharges"]["multi_house_surcharge"]) == Decimal("35000000")
        assert Decimal(result["total_tax"]) == Decimal("42000000")

    def test_조정_2주택_10억_85초과_법정합계(self) -> None:
        """10억, 100m², 조정 2주택: 8% 8천만 + 농특세 0.6% 600만 + 지방교육세 0.4% 400만 = 9천만원."""
        result = call(price="1000000000", house_count=2, is_regulated=True, area_m2="100", year=2026)
        assert Decimal(result["acquisition_tax"]) == Decimal("80000000")
        assert Decimal(result["surcharges"]["rural_special"]) == Decimal("6000000")
        assert Decimal(result["surcharges"]["local_edu"]) == Decimal("4000000")
        assert Decimal(result["total_tax"]) == Decimal("90000000")

    def test_acquisition_tax_2house_non_regulated_no_surcharge(self) -> None:
        """비조정 2주택 -> 중과 없음, 표준세율."""
        result = call(price="500000000", house_count=2, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["surcharges"]["multi_house_surcharge"]) == Decimal("0")
        assert result["heavy_applied"] is False

    def test_비조정_3주택은_8퍼센트(self) -> None:
        """지방세법 제13조의2제1항제2호: 비조정 3주택 8%."""
        result = call(price="500000000", house_count=3, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["applied_rate"]) == Decimal("0.08")
        assert Decimal(result["acquisition_tax"]) == Decimal("40000000")

    def test_비조정_4주택은_12퍼센트(self) -> None:
        """같은 항 제3호: 비조정 4주택 이상 12%."""
        result = call(price="500000000", house_count=4, is_regulated=False, area_m2="60", year=2026)
        assert Decimal(result["applied_rate"]) == Decimal("0.12")
        assert Decimal(result["acquisition_tax"]) == Decimal("60000000")

    def test_법인_취득_12퍼센트(self) -> None:
        """같은 항 제1호: 법인 12%. 100m²: 농특세 1.0% 500만, 지방교육세 0.4% 200만."""
        result = call(
            price="500000000", house_count=1, is_regulated=False, area_m2="100", year=2026,
            is_corporate=True,
        )
        assert Decimal(result["acquisition_tax"]) == Decimal("60000000")
        assert Decimal(result["surcharges"]["rural_special"]) == Decimal("5000000")
        assert Decimal(result["surcharges"]["local_edu"]) == Decimal("2000000")
        assert Decimal(result["total_tax"]) == Decimal("67000000")

    def test_중과_제외_주택은_표준세율(self) -> None:
        """일시적 2주택 등 중과 제외: 조정 2주택이라도 표준세율 1%."""
        result = call(
            price="500000000", house_count=2, is_regulated=True, area_m2="60", year=2026,
            is_heavy_excluded=True,
        )
        assert Decimal(result["applied_rate"]) == Decimal("0.01")
        assert Decimal(result["total_tax"]) == Decimal("5500000")

    def test_acquisition_tax_rural_special_large_area(self) -> None:
        """전용면적 85m² 초과 -> 농어촌특별세 0.2% 부과."""
        result = call(price="600000000", house_count=1, is_regulated=False, area_m2="100", year=2026)
        # 0.2% of 6억 = 1,200,000
        assert Decimal(result["surcharges"]["rural_special"]) == Decimal("1200000")

    def test_acquisition_tax_rural_special_small_area(self) -> None:
        """전용면적 85m² 이하 -> 농어촌특별세 없음."""
        result = call(price="600000000", house_count=1, is_regulated=False, area_m2="85", year=2026)
        assert Decimal(result["surcharges"]["rural_special"]) == Decimal("0")

    def test_acquisition_tax_policy_version(self) -> None:
        result = call(price="600000000", house_count=1, is_regulated=False, area_m2="60", year=2026)
        pv = result["policy_version"]
        assert pv["year"] == 2026
        assert result["policy_citations"]

    def test_acquisition_tax_zero_price_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            call(price="0", house_count=1, is_regulated=False, area_m2="60", year=2026)
