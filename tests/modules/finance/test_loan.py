"""Tests for finance loan schedule tool."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestLoanEqualPayment:
    def test_loan_equal_payment_100M_3pct_360m(self) -> None:
        """Principal 100M KRW, 3% annual, 360 months -> monthly ~ 421604 KRW."""
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="100000000",
            annual_rate="0.03",
            months=360,
            method="EQUAL_PAYMENT",
            rounding="HALF_EVEN",
            decimals=0,
        )
        payment = Decimal(result["monthly_payment"])
        assert abs(payment - Decimal("421604")) <= 1
        schedule = result["schedule"]
        assert len(schedule) == 360
        assert "trace" in result

    def test_loan_final_balance_zero_equal_payment(self) -> None:
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="10000000",
            annual_rate="0.06",
            months=12,
            method="EQUAL_PAYMENT",
            decimals=0,
        )
        last = result["schedule"][-1]
        assert last["balance"] == "0"

    def test_loan_equal_payment_structure(self) -> None:
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="1200000",
            annual_rate="0.12",
            months=12,
            method="EQUAL_PAYMENT",
            decimals=0,
        )
        schedule = result["schedule"]
        for row in schedule:
            assert "month" in row
            assert "payment" in row
            assert "principal" in row
            assert "interest" in row
            assert "balance" in row
        # Interest should decrease over time for equal payment method
        assert Decimal(schedule[0]["interest"]) > Decimal(schedule[-1]["interest"])

    def test_loan_equal_payment_interest_formula(self) -> None:
        """First month interest = principal * monthly_rate."""
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="1200000",
            annual_rate="0.12",
            months=12,
            method="EQUAL_PAYMENT",
            decimals=0,
        )
        first = result["schedule"][0]
        expected_interest = Decimal("1200000") * Decimal("0.12") / 12
        assert abs(Decimal(first["interest"]) - expected_interest) <= 1


class TestLoanEqualPrincipal:
    def test_loan_equal_principal_12M_12pct_12mo(self) -> None:
        """principal=12M, 12% annual, 12 months -> first month principal=1M, interest=120K."""
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="12000000",
            annual_rate="0.12",
            months=12,
            method="EQUAL_PRINCIPAL",
            decimals=0,
        )
        assert result["monthly_payment"] is None
        schedule = result["schedule"]
        assert len(schedule) == 12

        first = schedule[0]
        assert first["principal"] == "1000000"
        assert first["interest"] == "120000"
        assert first["balance"] == "11000000"

    def test_loan_final_balance_zero_equal_principal(self) -> None:
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="12000000",
            annual_rate="0.12",
            months=12,
            method="EQUAL_PRINCIPAL",
            decimals=0,
        )
        last = result["schedule"][-1]
        assert last["balance"] == "0"

    def test_loan_equal_principal_decreasing_payment(self) -> None:
        """Equal principal: payment decreases each month."""
        result = REGISTRY.invoke(
            "finance.loan_schedule",
            principal="12000000",
            annual_rate="0.12",
            months=12,
            method="EQUAL_PRINCIPAL",
            decimals=0,
        )
        schedule = result["schedule"]
        payments = [Decimal(r["payment"]) for r in schedule]
        for i in range(len(payments) - 1):
            assert payments[i] >= payments[i + 1]


class TestLoanValidation:
    def test_loan_invalid_method_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.loan_schedule",
                principal="1000000",
                annual_rate="0.05",
                months=12,
                method="INVALID",
            )

    def test_loan_zero_months_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.loan_schedule",
                principal="1000000",
                annual_rate="0.05",
                months=0,
            )

    def test_loan_negative_principal_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.loan_schedule",
                principal="-1000000",
                annual_rate="0.05",
                months=12,
            )

    def test_loan_negative_rate_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.loan_schedule",
                principal="1000000",
                annual_rate="-0.05",
                months=12,
            )
