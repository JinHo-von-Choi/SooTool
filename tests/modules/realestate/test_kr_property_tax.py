"""Tests for realestate.kr_property_tax.

기대값은 지방세법 제110조·제111조·제111조의2·제112조·제151조와 같은 법 시행령
제109조·제109조의2에서 직접 계산한 값이다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("realestate.kr_property_tax", **kwargs)


class TestPropertyTax:
    def test_500M_published(self):
        """공시가 5억 → 과세표준 3억; 6000만*0.1% + 9000만*0.15% + 1.5억*0.25% = 6만+13.5만+37.5만 = 57만"""
        r = call(published_price="500000000", year=2026, include_urban=False)
        # 과세표준 = 5억 * 0.6 = 3억
        assert Decimal(r["taxable_base"]) == Decimal("300000000")
        expected_prop = (
            Decimal("60000000")  * Decimal("0.001")
            + Decimal("90000000") * Decimal("0.0015")
            + Decimal("150000000") * Decimal("0.0025")
        )
        assert Decimal(r["property_tax"]) == expected_prop.quantize(Decimal("1"))
        assert r["special_rate_applied"] is False

    def test_with_urban_surcharge(self):
        """도시지역분 = 3억 × 0.14% = 42만."""
        r = call(published_price="500000000", year=2026, include_urban=True)
        assert Decimal(r["surcharges"]["urban_area"]) == Decimal("420000")

    def test_local_edu_is_20pct_of_property_tax(self):
        r = call(published_price="500000000", year=2026, include_urban=False)
        pt = Decimal(r["property_tax"])
        le = Decimal(r["surcharges"]["local_edu"])
        # 20% with FLOOR rounding
        assert le <= pt * Decimal("0.20")
        assert le >= pt * Decimal("0.20") - Decimal("1")

    def test_1세대1주택_5억_비율_44퍼센트_특례세율(self):
        """시가표준액 5억 → 공정시장가액비율 44%, 과표 2.2억.
        특례세율: 6천만×0.05% 3만 + 9천만×0.1% 9만 + 7천만×0.2% 14만 = 26만.
        지방교육세 5.2만, 도시지역분 2.2억 × 0.14% = 30.8만.
        """
        r = call(published_price="500000000", year=2026, is_one_house=True)
        assert Decimal(r["fair_market_ratio"]) == Decimal("0.44")
        assert Decimal(r["taxable_base"]) == Decimal("220000000")
        assert r["special_rate_applied"] is True
        assert Decimal(r["property_tax"]) == Decimal("260000")
        assert Decimal(r["surcharges"]["local_edu"]) == Decimal("52000")
        assert Decimal(r["surcharges"]["urban_area"]) == Decimal("308000")
        assert Decimal(r["total_tax"]) == Decimal("620000")

    def test_1세대1주택_2억_비율_43퍼센트(self):
        """시가표준액 2억 → 43%, 과표 8,600만. 특례세율 3만 + 2,600만×0.1% 2.6만 = 5.6만."""
        r = call(published_price="200000000", year=2026, is_one_house=True, include_urban=False)
        assert Decimal(r["fair_market_ratio"]) == Decimal("0.43")
        assert Decimal(r["property_tax"]) == Decimal("56000")

    def test_1세대1주택_9억_초과_특례세율_미적용(self):
        """시가표준액 10억 → 45%, 과표 4.5억. 표준세율 57만 + 1.5억×0.4% 60만 = 117만."""
        r = call(published_price="1000000000", year=2026, is_one_house=True, include_urban=False)
        assert Decimal(r["fair_market_ratio"]) == Decimal("0.45")
        assert r["special_rate_applied"] is False
        assert Decimal(r["property_tax"]) == Decimal("1170000")

    def test_과세표준상한(self):
        """5억(직전 연도 4억): 상한 = 4억×60% + 3억×5% = 2.55억 < 3억.
        세액 6만 + 13.5만 + 1.05억×0.25% 26.25만 = 45.75만, 도시지역분 35.7만.
        """
        r = call(published_price="500000000", year=2026, prior_year_published_price="400000000")
        assert Decimal(r["tax_base_cap"]) == Decimal("255000000")
        assert Decimal(r["taxable_base"]) == Decimal("255000000")
        assert Decimal(r["property_tax"]) == Decimal("457500")
        assert Decimal(r["surcharges"]["urban_area"]) == Decimal("357000")

    def test_과세표준상한_미달시_본래_과표(self):
        """직전 연도 5억이면 상한 3억 + 0.15억 > 3억 → 과표 3억 유지."""
        r = call(published_price="500000000", year=2026, prior_year_published_price="500000000")
        assert Decimal(r["taxable_base"]) == Decimal("300000000")

    def test_zero_published_raises(self):
        with pytest.raises(InvalidInputError):
            call(published_price="0", year=2026)

    def test_trace(self):
        r = call(published_price="500000000", year=2026)
        assert r["trace"]["tool"] == "realestate.kr_property_tax"
        assert "policy_version" in r
        assert r["policy_citations"]
