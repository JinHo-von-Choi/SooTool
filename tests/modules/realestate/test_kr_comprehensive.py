"""Tests for realestate.kr_comprehensive.

기대값은 종합부동산세법 제8조~제10조, 같은 법 시행령 제4조의3·제5조, 농어촌특별세법
제5조제1항제8호의 산식으로 직접 계산한 값이다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError, PolicyNotEnactedError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("realestate.kr_comprehensive", **kwargs)


class TestComprehensive:
    def test_1house_below_threshold_zero(self):
        """1주택 10억: 12억 공제 기준 미달 → 세액 0."""
        r = call(total_published_price="1000000000", year=2026, house_count=1)
        assert Decimal(r["total_tax"]) == Decimal("0")

    def test_1house_20억(self):
        """1주택 공시가 20억: 공제 12억, 과세표준 = (20-12) * 0.6 = 4.8억
           2주택 이하 구간: 3억*0.5% + 1.8억*0.7% = 150만 + 126만 = 276만
        """
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert Decimal(r["taxable_base"]) == Decimal("480000000")
        expected_base = Decimal("300000000") * Decimal("0.005") \
                      + Decimal("180000000") * Decimal("0.007")
        assert Decimal(r["base_tax"]) == expected_base.quantize(Decimal("1"))

    def test_1house_20억_재산세_공제(self):
        """재산세 공제 = 4.8억 × 재산세 1세대1주택 공정시장가액비율 45% × 0.4% = 86.4만.

        부과 재산세를 주지 않으면 합산 표준세율 재산세(9억 과표 → 297만)를 부과액으로 보므로
        공제액은 분자와 같다. 종부세 276만 - 86.4만 = 189.6만, 농특세 37.92만.
        """
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert Decimal(r["property_tax_levied"]) == Decimal("2970000")
        assert Decimal(r["property_tax_credit"]) == Decimal("864000")
        assert Decimal(r["comprehensive_tax"]) == Decimal("1896000")
        assert Decimal(r["rural_tax"]) == Decimal("379200")
        assert Decimal(r["total_tax"]) == Decimal("2275200")

    def test_1house_연령_보유_공제_80퍼센트_한도(self):
        """만 70세(40%) + 보유 15년(50%) = 90% → 한도 80%. 189.6만 × 80% = 151.68만 공제."""
        r = call(total_published_price="2000000000", year=2026, house_count=1, age=70, holding_years=15)
        assert Decimal(r["one_house_credit"]) == Decimal("1516800")
        assert Decimal(r["comprehensive_tax"]) == Decimal("379200")
        assert Decimal(r["rural_tax"]) == Decimal("75840")

    def test_1house_연령_보유_공제_합산(self):
        """만 62세(20%) + 보유 7년(20%) = 40%. 189.6만 × 40% = 75.84만."""
        r = call(total_published_price="2000000000", year=2026, house_count=1, age=62, holding_years=7)
        assert Decimal(r["one_house_credit"]) == Decimal("758400")
        assert Decimal(r["comprehensive_tax"]) == Decimal("1137600")

    def test_2주택은_일반세율표(self):
        """종부세법 제9조제1항제1호: 2주택 이하. 합계 30억, 공제 9억, 과표 12.6억.

        960만 + 0.6억 × 1.3% = 1,038만 (3주택 이상 표라면 1,080만).
        """
        r = call(total_published_price="3000000000", year=2026, house_count=2)
        assert Decimal(r["taxable_base"]) == Decimal("1260000000")
        assert r["rate_table"] == "two_or_fewer"
        assert Decimal(r["base_tax"]) == Decimal("10380000")

    def test_2주택_부과_재산세_입력_공제(self):
        """공제 = 500만 × (12.6억 × 60% × 0.4% = 302.4만) / (18억 과표 표준세율 재산세 657만)
        = 2,301,369.86... → 원 미만 절사 2,301,369. 종부세 1,038만 - 2,301,369 = 8,078,631.
        """
        r = call(
            total_published_price="3000000000", year=2026, house_count=2,
            property_tax_levied="5000000",
        )
        assert Decimal(r["property_tax_credit"]) == Decimal("2301369")
        assert Decimal(r["comprehensive_tax"]) == Decimal("8078631")

    def test_multi_house_uses_9억_deduction(self):
        r = call(total_published_price="2000000000", year=2026, house_count=3)
        assert Decimal(r["deduction"]) == Decimal("900000000")

    def test_multi_house_higher_rate(self):
        """다주택 20억: 공제 9억, 과세표준 = (20-9)*0.6 = 6.6억
           3주택 이상 3억*0.5% + 3억*0.7% + 0.6억*1.0% = 150만+210만+60만 = 420만
           재산세 공제 = 6.6억 × 60% × 0.4% = 158.4만 → 종부세 261.6만
        """
        r = call(total_published_price="2000000000", year=2026, house_count=3)
        assert Decimal(r["taxable_base"]) == Decimal("660000000")
        expected = Decimal("300000000") * Decimal("0.005") \
                 + Decimal("300000000") * Decimal("0.007") \
                 + Decimal("60000000")  * Decimal("0.010")
        assert Decimal(r["base_tax"]) == expected.quantize(Decimal("1"))
        assert Decimal(r["property_tax_credit"]) == Decimal("1584000")
        assert Decimal(r["comprehensive_tax"]) == Decimal("2616000")

    def test_세부담상한_150퍼센트(self):
        """1주택 20억, 직전 연도 총세액 300만: 올해 재산세 297만 + 종부세 189.6만 = 486.6만,
        상한 450만 → 초과 36.6만을 종부세에서 뺌 → 153만, 농특세 30.6만.
        """
        r = call(
            total_published_price="2000000000", year=2026, house_count=1,
            prior_year_total_tax="3000000",
        )
        assert Decimal(r["burden_cap_reduction"]) == Decimal("366000")
        assert Decimal(r["comprehensive_tax"]) == Decimal("1530000")
        assert Decimal(r["rural_tax"]) == Decimal("306000")

    def test_법인_단일세율_공제_0원_상한_미적용(self):
        """법인 2주택 10억: 공제 0, 과표 6억 × 2.7% = 1,620만. 재산세 공제 6억×60%×0.4% = 144만.
        세부담상한은 법인 단일세율에 적용하지 않는다.
        """
        r = call(
            total_published_price="1000000000", year=2026, house_count=2,
            is_corporate=True, prior_year_total_tax="1000000",
        )
        assert Decimal(r["deduction"]) == Decimal("0")
        assert Decimal(r["base_tax"]) == Decimal("16200000")
        assert Decimal(r["property_tax_credit"]) == Decimal("1440000")
        assert Decimal(r["burden_cap_reduction"]) == Decimal("0")
        assert Decimal(r["comprehensive_tax"]) == Decimal("14760000")

    def test_rural_special_is_20pct(self):
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert Decimal(r["rural_tax"]) <= Decimal(r["comprehensive_tax"]) * Decimal("0.20")

    def test_zero_count_raises(self):
        with pytest.raises(InvalidInputError):
            call(total_published_price="1000000000", year=2026, house_count=0)

    def test_zero_price_raises(self):
        with pytest.raises(InvalidInputError):
            call(total_published_price="0", year=2026, house_count=1)

    def test_trace(self):
        r = call(total_published_price="2000000000", year=2026, house_count=1)
        assert r["trace"]["tool"] == "realestate.kr_comprehensive"
        assert r["policy_status"] == "enacted"


class TestComprehensive2027Proposed:
    """정부 개정안(의안 제2221046호) 기준 2027년 개정안 버전."""

    def test_2027_requires_include_proposed(self):
        with pytest.raises(PolicyNotEnactedError):
            call(total_published_price="2000000000", year=2027, house_count=1)

    def test_2027_비거주_1주택_14억_이하_납세의무_없음(self):
        """안 제7조제1항: 1세대 1주택자는 공시가격 합계 14억 초과일 때 납세의무."""
        r = call(total_published_price="1300000000", year=2027, house_count=1, include_proposed=True)
        assert Decimal(r["total_tax"]) == Decimal("0")
        assert r["policy_status"] == "proposed"

    def test_2027_거주_1주택_20억(self):
        """거주 공제 14억, 과표 6억 × 70% = 4.2억. 2027 세율: 150만 + 1.2억 × 0.7% = 234만.
        재산세 공제 4.2억 × 60% × 0.4% = 100.8만 → 133.2만.
        만 66세 30% + max(거주 12년 40%, 보유 12년 20%) = 70% → 93.24만 공제(800만 한도 내).
        종부세 39.96만, 농특세 7.992만.
        """
        r = call(
            total_published_price="2000000000", year=2027, house_count=1,
            resident_house_price="2000000000", age=66, holding_years=12, residence_years=12,
            include_proposed=True,
        )
        assert Decimal(r["deduction"]) == Decimal("1400000000")
        assert Decimal(r["taxable_base"]) == Decimal("420000000")
        assert Decimal(r["base_tax"]) == Decimal("2340000")
        assert Decimal(r["property_tax_credit"]) == Decimal("1008000")
        assert Decimal(r["one_house_credit"]) == Decimal("932400")
        assert Decimal(r["comprehensive_tax"]) == Decimal("399600")
        assert Decimal(r["rural_tax"]) == Decimal("79920")

    def test_2027_다주택_기본공제_산식(self):
        """2주택 합계 20억, 거주주택 10억: 공제 4억 + 5억 × 10/20 = 6.5억.
        과표 13.5억 × 70% = 9.45억, 2027 2주택 이하 세율: 360만 + 3.45억 × 1.3% = 808.5만.
        """
        r = call(
            total_published_price="2000000000", year=2027, house_count=2,
            resident_house_price="1000000000", include_proposed=True,
        )
        assert Decimal(r["deduction"]) == Decimal("650000000")
        assert Decimal(r["taxable_base"]) == Decimal("945000000")
        assert Decimal(r["base_tax"]) == Decimal("8085000")
