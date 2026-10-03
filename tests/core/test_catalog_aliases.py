from __future__ import annotations

import pytest

from sootool import server
from sootool.core.catalog import search_tools
from sootool.core.registry import REGISTRY
from sootool.core.tool_aliases import ALIASES


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def test_every_alias_entry_points_to_a_registered_tool():
    names = {e.full_name for e in REGISTRY.list()}
    assert not [n for n in ALIASES if n not in names]


def test_aliases_are_non_empty_and_unique_per_tool():
    for name, aliases in ALIASES.items():
        assert aliases, name
        assert len(set(a.lower() for a in aliases)) == len(aliases), name


# 사용자가 실제로 칠 법한 질의와, 상위 3위 안에 있어야 하는 도구.
_QUERIES = [
    ("양도세", "tax.capital_gains_kr"),
    ("집 팔 때 세금", "realestate.kr_transfer_tax"),
    ("취득세", "realestate.kr_acquisition_tax"),
    ("종부세", "realestate.kr_comprehensive"),
    ("재산세", "realestate.kr_property_tax"),
    ("연봉 실수령액", "payroll.kr_salary"),
    ("세후 월급", "payroll.kr_salary"),
    ("퇴직금", "payroll.kr_severance_pay"),
    ("연말정산", "payroll.kr_year_end_tax_settlement"),
    ("시급 알바 월급", "payroll.hourly_to_monthly_net"),
    ("증여세", "tax.kr_gift"),
    ("상속세", "tax.kr_inheritance"),
    ("법인세", "tax.kr_corporate"),
    ("간이과세 부가세", "tax.kr_simplified_vat"),
    ("부가세 역산", "accounting.vat_extract"),
    ("감가상각 정액법", "accounting.depreciation_straight_line"),
    ("대출 원리금균등 상환", "finance.loan_schedule"),
    ("복리 미래가치", "finance.fv"),
    ("현재가치", "finance.pv"),
    ("내부수익률", "finance.irr"),
    ("만나이", "datetime.age"),
    ("영업일 수", "datetime.count_business_days"),
    ("음력 양력 변환", "datetime.lunar_to_solar"),
    ("추석", "datetime.lunar_holiday"),
    ("환율 환전", "units.fx_convert"),
    ("비만도", "medical.bmi"),
    ("t 검정 두 집단", "stats.ttest_two_sample"),
    ("회귀분석", "stats.regression_linear"),
    ("신뢰구간", "stats.ci_mean"),
    ("크리티컬 패스", "pm.critical_path"),
    ("net salary korea", "payroll.kr_salary"),
    ("loan amortization", "finance.loan_schedule"),
    ("compound interest", "finance.fv"),
    ("business days between dates", "datetime.count_business_days"),
    ("capital gains tax us", "tax_us.capital_gains"),
    ("계산기 sqrt", "core.calc"),
    ("영수증 검증", "sootool.verify_receipt"),
    ("여러 건 일괄 계산", "core.batch"),
    ("세후 300만원이면 세전 월급", "payroll.kr_gross_from_net"),
    ("역산 목표값 찾기", "core.solve_for"),
    ("시나리오 비교", "core.compare"),
    ("계산 과정 설명", "core.explain"),
]


@pytest.mark.parametrize(("query", "expected"), _QUERIES, ids=[q for q, _ in _QUERIES])
def test_realistic_queries_find_the_intended_tool_in_the_top_three(query, expected):
    names = [hit["name"] for hit in search_tools(REGISTRY, query, limit=3)]
    assert expected in names, names


def test_alias_match_outranks_a_weak_description_match():
    hits = search_tools(REGISTRY, "양도세", limit=5)
    assert hits[0]["name"] in {"tax.capital_gains_kr", "realestate.kr_transfer_tax"}
