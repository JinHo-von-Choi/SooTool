"""세목 간 절사·반올림 규칙이 어긋나지 않는지 감시한다.

2026-10-30 점검에서 같은 산출세액(종합소득 기본세율 적용 결과)을 두 도구가 서로 다른
반올림 정책으로 계산해 1원씩 갈리는 것이 확인됐다.

- ``tax.kr_comprehensive_income_tax``      : 산출세액 원 미만 버림(DOWN)
- ``payroll.kr_year_end_tax_settlement``   : 산출세액 원 미만 반올림(HALF_UP) → DOWN 으로 정정

같은 법리 양상(종합소득 기본세율 산출세액)에는 같은 절사 규칙이 적용되어야 하므로,
각 도구가 보고한 과세표준을 그대로 _calc_progressive 에 넣어 같은 값이 나오는지 확인한다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policy_mgmt.loader import load as policy_load


def _brackets(year: int = 2026) -> list[dict]:
    """종합소득 기본세율 구간표(소득세법 제55조제1항)."""
    return policy_load("tax", "kr_income", year)["data"]["brackets"]


def _expected(taxable: str, year: int = 2026) -> Decimal:
    tax, _eff, _marg, _bd = _calc_progressive(
        Decimal(taxable), _brackets(year), RoundingPolicy.DOWN, 0
    )
    return tax


@pytest.mark.parametrize(
    "annual_gross",
    ["20000000", "26095678", "33333333", "45000000", "60000000"],
)
def test_year_end_settlement_truncates_san_output_tax(annual_gross: str) -> None:
    """연말정산 도구의 산출세액은 원 미만 절사(DOWN) 결과와 일치한다."""
    r = REGISTRY.invoke(
        "payroll.kr_year_end_tax_settlement",
        annual_gross=annual_gross,
        prepaid_tax="0",
        year=2026,
    )
    assert Decimal(r["computed_tax"]) == _expected(r["taxable_income"])


@pytest.mark.parametrize(
    "total_salary",
    ["20000000", "26095678", "33333333", "45000000", "60000000"],
)
def test_comprehensive_tax_truncates_san_output_tax(total_salary: str) -> None:
    """종합소득세 신고 도구의 산출세액도 원 미만 절사(DOWN) 결과와 일치한다."""
    r = REGISTRY.invoke(
        "tax.kr_comprehensive_income_tax",
        year=2026,
        total_salary=total_salary,
        dependents=1,
    )
    assert Decimal(r["computed_tax"]) == _expected(r["taxable_income"])


def test_both_tools_use_the_same_truncation_rule() -> None:
    """두 도구가 같은 과세표준에서 같은 산출세액을 낸다(절사 규칙이 같아야 성립)."""
    year_end = REGISTRY.invoke(
        "payroll.kr_year_end_tax_settlement",
        annual_gross="33333333", prepaid_tax="0", year=2026,
    )
    comprehensive = REGISTRY.invoke(
        "tax.kr_comprehensive_income_tax",
        year=2026, total_salary="33333333", dependents=1,
    )
    # 과세표준은 근로소득공제 표가 달라 서로 다르지만, 산출세액 규칙은 같아야 한다.
    assert Decimal(year_end["computed_tax"]) == _expected(year_end["taxable_income"])
    assert Decimal(comprehensive["computed_tax"]) == _expected(comprehensive["taxable_income"])


def test_truncation_is_not_rounding() -> None:
    """절사와 반올림이 갈리는 과세표준에서 도구가 절사 값을 낸다."""
    brackets = _brackets()
    divergent = [
        taxable for taxable in
        ("9999999", "12345678", "15431327", "33333333", "45678901", "66666666")
        if _calc_progressive(Decimal(taxable), brackets, RoundingPolicy.DOWN, 0)[0]
        != _calc_progressive(Decimal(taxable), brackets, RoundingPolicy.HALF_UP, 0)[0]
    ]
    assert divergent, "절사와 반올림이 갈리는 표본이 하나도 없다(테스트가 무의미해짐)"

    for taxable in divergent:
        down = _calc_progressive(Decimal(taxable), brackets, RoundingPolicy.DOWN, 0)[0]
        half = _calc_progressive(Decimal(taxable), brackets, RoundingPolicy.HALF_UP, 0)[0]
        assert down < half
        assert down == down.to_integral_value(rounding="ROUND_DOWN")


def test_local_income_tax_truncates_to_won() -> None:
    """지방소득세는 원 미만 버림(DOWN)이다."""
    r = REGISTRY.invoke("tax.kr_local_income_tax", income_tax="1234567")
    assert Decimal(r["local_income_tax"]) == Decimal("123456")


def test_local_income_tax_matches_comprehensive_tax_local_column() -> None:
    """종합소득세 신고 도구의 지방세 열과 지방소득세 도구의 결과가 같아야 한다."""
    comprehensive = REGISTRY.invoke(
        "tax.kr_comprehensive_income_tax",
        year=2026, total_salary="45000000", dependents=1,
    )
    local = REGISTRY.invoke(
        "tax.kr_local_income_tax", income_tax=comprehensive["decided_tax"]
    )
    assert local["local_income_tax"] == comprehensive["local_income_tax"]
