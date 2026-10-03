"""Tests for payroll.kr_salary.

Author: 최진호
Modified: 2026-10-03

기대값은 국민연금법 부칙(법률 제20903호) 제4조 4.75%, 국민연금공단 기준소득월액 상·하한 공지,
국민건강보험법 시행령 제44조 7.19%, 보건복지부고시 제2025-222호 보험료 상·하한,
노인장기요양보험법 시행령 제4조 0.9448%와 같은 법 제9조제1항(2026년 11월분부터 비율 반올림),
고용보험 실업급여 보험료율 1.8%의 2분의 1, 소득세법 시행령 별표 2 간이세액표에서 직접 계산했다.
"""
from __future__ import annotations

import concurrent.futures
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
import yaml

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policy_mgmt.validators import validate_policy

_POLICY_DIR = Path(__file__).resolve().parents[3] / "src" / "sootool" / "policies" / "payroll"
_VERSION_FILES = (
    "kr_4insurance_2026.yaml",
    "kr_4insurance_2026@2026-07-01.yaml",
    "kr_4insurance_2026@2026-11-01.yaml",
)


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_salary", **kwargs)


def _doc(name: str) -> dict:
    return yaml.safe_load((_POLICY_DIR / name).read_text(encoding="utf-8"))


class TestInsurancePolicyFiles:
    @pytest.mark.parametrize("name", _VERSION_FILES)
    def test_validates(self, name):
        report = validate_policy((_POLICY_DIR / name).read_text(encoding="utf-8"), "payroll", "kr_4insurance")
        assert report["status"] == "ok", report["findings"]

    def test_periods_cover_2026_without_gap(self):
        docs = [_doc(name) for name in _VERSION_FILES]
        assert str(docs[0]["effective_date"]) == "2026-01-01"
        assert str(docs[-1]["effective_to"]) == "2026-12-31"
        for current, following in zip(docs, docs[1:], strict=False):
            end = date.fromisoformat(str(current["effective_to"]))
            assert date.fromisoformat(str(following["effective_date"])) == end + timedelta(days=1)

    def test_long_term_care_ratio_matches_rates(self):
        """비율 = 장기요양보험료율 0.9448% / 건강보험료율 7.19%. 11월분부터 소수점 이하 다섯째자리에서 반올림."""
        ratio = Decimal("0.9448") / Decimal("7.19")
        jan   = Decimal(_doc(_VERSION_FILES[0])["data"]["health_insurance"]["long_term_care_rate_of_health"])
        nov   = Decimal(_doc(_VERSION_FILES[2])["data"]["health_insurance"]["long_term_care_rate_of_health"])
        assert abs(jan - ratio) < Decimal("1E-18")
        assert nov == ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class TestKrSalaryBasic:
    def test_3million_with_meal(self):
        r = call(monthly_salary="3000000", year=2026, meal_allowance="200000")
        gross = Decimal(r["gross"])
        net   = Decimal(r["net"])
        assert gross == Decimal("3000000")
        assert Decimal(r["non_taxable"]) == Decimal("200000")
        assert Decimal(r["taxable"])     == Decimal("2800000")
        assert net < gross
        # sanity: deductions sum
        total_ded = (
            Decimal(r["insurances"]["total"])
            + Decimal(r["taxes"]["total"])
        )
        assert net == gross - total_ded

    def test_meal_capped_at_200k(self):
        r = call(monthly_salary="5000000", year=2026, meal_allowance="500000")
        assert Decimal(r["non_taxable"]) == Decimal("200000")
        assert Decimal(r["taxable"])     == Decimal("4800000")

    def test_national_pension_clipped_to_cap(self):
        """기준소득월액 상한: 2026.7.1. 이후 6,590,000 x 4.75% = 313,025."""
        r = call(monthly_salary="20000000", year=2026, meal_allowance="0")
        assert Decimal(r["insurances"]["national_pension"]) == Decimal("313025")

    def test_national_pension_on_taxable_after_meal(self):
        """과세급여 2,800,000 x 4.75% = 133,000."""
        r = call(monthly_salary="3000000", year=2026, meal_allowance="200000")
        assert Decimal(r["insurances"]["national_pension"]) == Decimal("133000")

    def test_policy_version_exposed(self):
        r = call(monthly_salary="3000000", year=2026)
        pv = r["policy_version"]
        assert pv["year"] == 2026
        assert "sha256" in pv
        assert "effective_date" in pv

    def test_trace_present(self):
        r = call(monthly_salary="3000000", year=2026)
        assert "trace" in r
        assert r["trace"]["tool"] == "payroll.kr_salary"
        assert "formula" in r["trace"]


class TestKrSalaryStatutory:
    def test_3010k_family_1_full_breakdown(self):
        """월 3,010,000원, 공제대상가족 1명, 2026년 11월분 이후 기준."""
        r = call(monthly_salary="3010000", year=2026)
        ins = r["insurances"]
        assert ins["national_pension"]     == "142975"   # 3,010,000 x 4.75%
        assert ins["health_insurance"]     == "108200"   # 3,010,000 x 3.595% = 108,209.5, 원 단위 절사(10원 단위)
        assert ins["long_term_care"]       == "14210"    # 108,200 x 0.1314 = 14,217.48, 원 단위 절사
        assert ins["employment_insurance"] == "27090"    # 3,010,000 x 0.9%
        assert ins["industrial_accident"]  == "0"
        assert r["taxes"]["income_tax"]       == "74350"  # 간이세액표 3,000~3,020천원, 1명
        assert r["taxes"]["local_income_tax"] == "7435"
        assert r["net"] == "2635740"

    def test_3010k_family_2(self):
        r = call(monthly_salary="3010000", year=2026, num_dependents=2)
        assert r["taxes"]["income_tax"]       == "56850"
        assert r["taxes"]["local_income_tax"] == "5685"
        assert r["net"] == "2654990"

    def test_child_reduction_after_march(self):
        """가족 4명, 8세 이상 20세 이하 자녀 1명: 26,690 - 20,830 = 5,860."""
        r = call(monthly_salary="3010000", year=2026, num_dependents=4, children_8_20=1)
        assert r["taxes"]["income_tax"] == "5860"
        assert r["income_tax_lookup"]["child_reduction"] == "20830"

    def test_income_tax_uses_taxable_salary(self):
        """식대 200,000 비과세: 월급여액 2,810,000 으로 간이세액표 조회."""
        with_meal = call(monthly_salary="3010000", year=2026, meal_allowance="200000")
        assert with_meal["income_tax_lookup"]["salary_k"] == "2810"

    def test_long_term_care_ratio_before_november(self):
        """월 1,700,000원: 건강보험료 61,110 -> 절사 후 61,110.
        1~10월분 61,110 x 0.9448 / 7.19 = 8,030.14(절사 8,030), 11월분부터 x 0.1314 = 8,029.85(절사 8,020)."""
        r = call(monthly_salary="1700000", year=2026, as_of="2026-03-15")
        assert r["insurances"]["long_term_care"] == "8030"
        r = call(monthly_salary="1700000", year=2026, as_of="2026-10-31")
        assert r["insurances"]["long_term_care"] == "8030"
        r = call(monthly_salary="1700000", year=2026, as_of="2026-11-01")
        assert r["insurances"]["long_term_care"] == "8020"

    def test_national_pension_limits_by_period(self):
        """상한 6,370,000(2026.6.30.까지)과 6,590,000(2026.7.1.부터), 하한 400,000과 410,000."""
        high = {"monthly_salary": "20000000", "year": 2026}
        low  = {"monthly_salary": "300000",   "year": 2026}
        assert call(as_of="2026-06-30", **high)["insurances"]["national_pension"] == "302575"
        assert call(as_of="2026-07-01", **high)["insurances"]["national_pension"] == "313025"
        assert call(as_of="2026-06-30", **low)["insurances"]["national_pension"]  == "19000"
        assert call(as_of="2026-07-01", **low)["insurances"]["national_pension"]  == "19475"

    def test_national_pension_truncates_below_thousand(self):
        """소득월액 3,000,999원의 천원 미만 버림: 3,000,000 x 4.75% = 142,500."""
        r = call(monthly_salary="3000999", year=2026)
        assert r["insurances"]["national_pension"] == "142500"

    def test_health_insurance_monthly_floor(self):
        """보수월액보험료 하한 20,160원의 근로자 부담 10,080원. 장기요양 10,080 x 0.1314 = 1,324.5, 원 단위 절사 1,320."""
        r = call(monthly_salary="200000", year=2026)
        assert r["insurances"]["health_insurance"] == "10080"
        assert r["insurances"]["long_term_care"]   == "1320"

    def test_health_insurance_monthly_ceiling(self):
        """보수월액보험료 상한 9,183,480원의 근로자 부담 4,591,740원."""
        r = call(monthly_salary="200000000", year=2026)
        assert r["insurances"]["health_insurance"] == "4591740"

    def test_policy_versions_by_period(self):
        assert call(monthly_salary="3000000", year=2026, as_of="2026-02-01")["policy_effective_date"] == "2026-01-01"
        assert call(monthly_salary="3000000", year=2026, as_of="2026-08-01")["policy_effective_date"] == "2026-07-01"
        assert call(monthly_salary="3000000", year=2026)["policy_effective_date"] == "2026-11-01"

    def test_income_tax_non_decreasing_in_salary(self):
        """간이세액표 세액과 공제 합계는 월급에 대해 비감소다(행 경계 포함)."""
        previous_tax = Decimal("-1")
        previous_ded = Decimal("-1")
        for salary in range(2_990_000, 3_030_001, 500):
            r   = call(monthly_salary=str(salary), year=2026)
            tax = Decimal(r["taxes"]["income_tax"])
            ded = Decimal(r["insurances"]["total"]) + Decimal(r["taxes"]["total"])
            assert tax >= previous_tax
            assert ded >= previous_ded
            previous_tax, previous_ded = tax, ded


class TestKrSalaryValidation:
    def test_negative_salary_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="-100", year=2026)

    def test_zero_salary_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="0", year=2026)

    def test_negative_meal_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="3000000", year=2026, meal_allowance="-1")

    def test_meal_exceeds_salary_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="100000", year=2026, meal_allowance="200000")

    def test_zero_dependents_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="3000000", year=2026, num_dependents=0)

    def test_children_exceeding_family_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="3000000", year=2026, num_dependents=2, children_8_20=2)

    def test_negative_children_raises(self):
        with pytest.raises(InvalidInputError):
            call(monthly_salary="3000000", year=2026, children_8_20=-1)


class TestKrSalaryBatch:
    def test_payroll_batch_race_free(self) -> None:
        """Run kr_salary in 100 parallel core.batch calls (ADR-007)."""
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"pay-{i}",
                "tool": "payroll.kr_salary",
                "args": {"monthly_salary": "3000000", "year": 2026, "meal_allowance": "200000"},
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["net"] == first["net"]
            assert r["insurances"]["total"] == first["insurances"]["total"]

    def test_payroll_thread_pool_race_free(self):
        """Also verify via bare ThreadPoolExecutor."""
        def run(_):
            return call(monthly_salary="3500000", year=2026, meal_allowance="200000")

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            results = list(ex.map(run, range(50)))

        nets = {r["net"] for r in results}
        assert len(nets) == 1
