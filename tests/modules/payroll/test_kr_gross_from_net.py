"""Tests for payroll.kr_gross_from_net.

Author: 최진호
Date: 2026-10-03

실수령액은 간이세액표 행 경계와 국민연금 천원 단위 경계에서 줄어들 수 있으므로 단조가 아니다.
반환 월급이 목표 실수령액을 만족하는 가장 작은 정수 월급인지를 경계 주변 전수 비교로 확인한다.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY


def inverse(**kwargs):
    return REGISTRY.invoke("payroll.kr_gross_from_net", **kwargs)


def net_of(salary: int, **kwargs) -> Decimal:
    return Decimal(REGISTRY.invoke("payroll.kr_salary", monthly_salary=str(salary), year=2026, **kwargs)["net"])


def deductions_of(salary: int) -> Decimal:
    r = REGISTRY.invoke("payroll.kr_salary", monthly_salary=str(salary), year=2026)
    return Decimal(r["insurances"]["total"]) + Decimal(r["taxes"]["total"])


class TestNonMonotoneNet:
    def test_net_drops_at_table_row_boundary(self):
        """2,999,999원(2,990~3,000천원 행 73,060원)에서 3,000,000원(74,350원)으로 넘어가면 실수령액이 준다."""
        assert net_of(3_000_000) < net_of(2_999_999)

    def test_deductions_are_non_decreasing(self):
        previous = Decimal("-1")
        for salary in range(2_998_000, 3_022_001, 250):
            current = deductions_of(salary)
            assert current >= previous
            previous = current


class TestSmallestGross:
    def test_target_from_statutory_net_is_reached_below_row_start(self):
        """월 3,010,000원의 법정 실수령액 2,635,723원은 그보다 작은 월급에서 이미 도달한다."""
        out   = inverse(net_monthly="2635723", year=2026)
        gross = int(out["gross"])
        assert gross <= 3_010_000
        assert Decimal(out["achieved_net"]) >= Decimal("2635723")
        assert all(net_of(g) < Decimal("2635723") for g in range(gross - 1500, gross))

    @pytest.mark.parametrize("net", ["2000000", "2635000", "3000000"])
    def test_no_smaller_salary_reaches_the_target(self, net):
        out   = inverse(net_monthly=net, year=2026)
        gross = int(out["gross"])
        assert Decimal(out["achieved_net"]) >= Decimal(net)
        assert all(net_of(g) < Decimal(net) for g in range(gross - 1000, gross))
        assert out["residual"] == str(Decimal(out["achieved_net"]) - Decimal(net))

    def test_meal_and_family_arguments_pass_through(self):
        out = inverse(net_monthly="3000000", year=2026, meal_allowance="200000", num_dependents=4, children_8_20=1)
        salary = out["salary"]
        assert salary["non_taxable"] == "200000"
        assert Decimal(salary["income_tax_lookup"]["child_reduction"]) > 0
        gross = int(out["gross"])
        args  = {"meal_allowance": "200000", "num_dependents": 4, "children_8_20": 1}
        assert all(net_of(g, **args) < Decimal("3000000") for g in range(gross - 500, gross))

    def test_rejects_non_positive_target(self):
        with pytest.raises(DomainConstraintError):
            inverse(net_monthly="0", year=2026)
