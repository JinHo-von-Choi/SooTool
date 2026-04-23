"""Tests for realestate.kr_local_property (광역자치단체별 취득세·재산세)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("realestate.kr_local_property", **kwargs)


class TestLocalPropertyAcquisition:
    def test_seoul_standard_acquisition(self):
        """서울 5억 → 1% bracket, coef 1.0, base=500만, 지방교육세=50만."""
        r = call(
            region="seoul",
            mode="acquisition",
            price="500000000",
            year=2026,
            area_m2="60",
        )
        assert Decimal(r["base_tax"]) == Decimal("5000000")
        assert Decimal(r["coefficient"]) == Decimal("1.00")
        assert Decimal(r["surcharges"]["local_edu"]) == Decimal("500000")
        assert Decimal(r["surcharges"]["rural_special"]) == Decimal("0")
        assert Decimal(r["total_tax"]) == Decimal("5500000")

    def test_sejong_half_reduction(self):
        """세종시는 취득세 50% 감면 → 5억 × 1% × 0.5 = 250만."""
        r = call(
            region="sejong",
            mode="acquisition",
            price="500000000",
            year=2026,
            area_m2="60",
        )
        assert Decimal(r["coefficient"]) == Decimal("0.50")
        assert Decimal(r["base_tax"]) == Decimal("2500000")
        # 지방교육세 0.1%는 base 기준이 아닌 price 기준 → 50만
        assert Decimal(r["surcharges"]["local_edu"]) == Decimal("500000")
        assert Decimal(r["total_tax"]) == Decimal("3000000")
        assert r["region"] == "sejong"

    def test_gyeonggi_rural_special_large_area(self):
        """경기 6억 85m² 초과 → 농특세 0.2% 부과."""
        r = call(
            region="gyeonggi",
            mode="acquisition",
            price="600000000",
            year=2026,
            area_m2="100",
        )
        # 6억 × 1% × 1.0 = 600만
        assert Decimal(r["base_tax"]) == Decimal("6000000")
        # 농특세 0.2% × 6억 = 120만
        assert Decimal(r["surcharges"]["rural_special"]) == Decimal("1200000")
        # 지방교육세 0.1% × 6억 = 60만
        assert Decimal(r["surcharges"]["local_edu"]) == Decimal("600000")
        assert Decimal(r["total_tax"]) == Decimal("7800000")
        assert r["policy_version"]["year"] == 2026

    def test_busan_high_price_bracket(self):
        """부산 12억 → 3% bracket 진입."""
        r = call(
            region="busan",
            mode="acquisition",
            price="1200000000",
            year=2026,
            area_m2="60",
        )
        # 3% × 12억 × 1.0 = 3,600만
        assert Decimal(r["base_tax"]) == Decimal("36000000")
        assert "trace" in r
        assert r["trace"]["tool"] == "realestate.kr_local_property"
        assert "region_coefficient" in [s["label"] for s in r["trace"]["steps"]]
        assert r["policy_sha256"] != ""


class TestLocalPropertyProperty:
    def test_seoul_property_tax(self):
        """서울 공시가 5억 → 과세표준 3억 × 누진세율 (60만+22만+30만=112만) × 1.0."""
        r = call(
            region="seoul",
            mode="property",
            price="500000000",
            year=2026,
        )
        # taxable = 500000000 * 0.6 = 300000000
        assert Decimal(r["taxable_base"]) == Decimal("300000000.00")
        # brackets: 6천만 0.1% = 6만, 6천~1.5억 0.15% = 9천만*0.0015=13.5만, 1.5억~3억 0.25%=1.5억*0.0025=37.5만
        # 6 + 13.5 + 37.5 = 57만
        assert Decimal(r["base_tax"]) == Decimal("570000")
        # 지방교육세 = 57만 × 20% = 11.4만
        assert Decimal(r["surcharges"]["local_edu"]) == Decimal("114000")
        # 도시지역분 = 3억 × 0.14% = 42만
        assert Decimal(r["surcharges"]["urban_area"]) == Decimal("420000")
        assert Decimal(r["total_tax"]) == Decimal("1104000")

    def test_sejong_no_urban_area(self):
        """세종시는 도시지역분 미적용 → urban=0."""
        r = call(
            region="sejong",
            mode="property",
            price="500000000",
            year=2026,
            include_urban=True,
        )
        assert Decimal(r["surcharges"]["urban_area"]) == Decimal("0")
        # base_tax는 동일
        assert Decimal(r["base_tax"]) == Decimal("570000")
        assert Decimal(r["surcharges"]["local_edu"]) == Decimal("114000")
        assert Decimal(r["total_tax"]) == Decimal("684000")
        assert r["region"] == "sejong"

    def test_include_urban_false_skips_urban(self):
        """include_urban=False 시 도시지역분 0."""
        r = call(
            region="incheon",
            mode="property",
            price="500000000",
            year=2026,
            include_urban=False,
        )
        assert Decimal(r["surcharges"]["urban_area"]) == Decimal("0")
        assert Decimal(r["total_tax"]) == Decimal("684000")
        assert "breakdown" in r
        assert len(r["breakdown"]) == 4


class TestLocalPropertyValidation:
    def test_unknown_region_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                region="jeju",
                mode="acquisition",
                price="500000000",
                year=2026,
                area_m2="60",
            )

    def test_unknown_mode_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                region="seoul",
                mode="invalid",
                price="500000000",
                year=2026,
                area_m2="60",
            )

    def test_zero_price_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                region="seoul",
                mode="acquisition",
                price="0",
                year=2026,
                area_m2="60",
            )

    def test_negative_area_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                region="seoul",
                mode="acquisition",
                price="500000000",
                year=2026,
                area_m2="-1",
            )

    def test_trace_structure(self):
        r = call(
            region="daegu",
            mode="acquisition",
            price="500000000",
            year=2026,
            area_m2="60",
        )
        assert r["trace"]["tool"] == "realestate.kr_local_property"
        assert "formula" in r["trace"]
        assert r["coefficient"] == "1.00"
        assert "policy_sha256" in r
        assert "policy_source" in r


class TestLocalPropertyBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"lp-{i}",
                "tool": "realestate.kr_local_property",
                "args": {
                    "region":  "seoul",
                    "mode":    "acquisition",
                    "price":   "500000000",
                    "year":    2026,
                    "area_m2": "60",
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        for r in response["results"]:
            assert r["result"]["base_tax"] == "5000000"
            assert r["result"]["total_tax"] == "5500000"
