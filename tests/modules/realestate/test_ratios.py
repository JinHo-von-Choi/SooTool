"""Tests for DSR, LTV, DTI ratio tools."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.realestate  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policies import UnsupportedPolicyError


class TestDSR:
    def test_dsr_below_cap(self) -> None:
        """annual_debt=3M, income=10M -> dsr=0.30, within_cap=True."""
        result = REGISTRY.invoke(
            "realestate.kr_dsr",
            annual_debt_payment="3000000",
            annual_income="10000000",
            year=2026,
        )
        dsr = Decimal(result["dsr"])
        assert abs(dsr - Decimal("0.30")) < Decimal("0.0001")
        assert result["within_cap"] is True
        assert "cap" in result
        assert "trace" in result

    def test_dsr_over_cap(self) -> None:
        """annual_debt=5M, income=10M -> dsr=0.50, within_cap=False."""
        result = REGISTRY.invoke(
            "realestate.kr_dsr",
            annual_debt_payment="5000000",
            annual_income="10000000",
            year=2026,
        )
        dsr = Decimal(result["dsr"])
        assert abs(dsr - Decimal("0.50")) < Decimal("0.0001")
        assert result["within_cap"] is False

    def test_dsr_at_exact_cap(self) -> None:
        """DSR exactly at 40% cap -> within_cap=True."""
        result = REGISTRY.invoke(
            "realestate.kr_dsr",
            annual_debt_payment="4000000",
            annual_income="10000000",
            year=2026,
        )
        assert result["within_cap"] is True

    def test_dsr_zero_income_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.kr_dsr",
                annual_debt_payment="1000000",
                annual_income="0",
                year=2026,
            )

    def test_dsr_policy_version_returned(self) -> None:
        result = REGISTRY.invoke(
            "realestate.kr_dsr",
            annual_debt_payment="3000000",
            annual_income="10000000",
            year=2026,
        )
        pv = result["policy_version"]
        assert pv["year"] == 2026
        assert "sha256" in pv

    def test_realestate_unsupported_year_dsr(self) -> None:
        with pytest.raises(UnsupportedPolicyError):
            REGISTRY.invoke(
                "realestate.kr_dsr",
                annual_debt_payment="3000000",
                annual_income="10000000",
                year=2099,
            )


class TestLTV:
    def test_ltv_first_house_regulated(self) -> None:
        """loan=3억, price=6억, regulated=True, count=1 -> ltv=0.50, within_cap=True."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="300000000",
            property_value="600000000",
            year=2026,
            is_regulated=True,
            house_count=1,
        )
        ltv = Decimal(result["ltv"])
        assert abs(ltv - Decimal("0.50")) < Decimal("0.0001")
        assert result["within_cap"] is True

    def test_ltv_multi_house_regulated_blocked(self) -> None:
        """2 houses, regulated=True -> max_loan=0, LTV cap=0."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="0",
            property_value="600000000",
            year=2026,
            is_regulated=True,
            house_count=2,
        )
        assert result["max_loan"] == "0"
        assert result["within_cap"] is True

    def test_ltv_multi_house_regulated_any_loan_fails(self) -> None:
        """Any loan > 0 with 2 houses in regulated area -> within_cap=False."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="1",
            property_value="600000000",
            year=2026,
            is_regulated=True,
            house_count=2,
        )
        assert result["within_cap"] is False

    def test_ltv_non_regulated_first_house(self) -> None:
        """Non-regulated, 1 house, loan=7억, price=10억 -> within cap (70%)."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="700000000",
            property_value="1000000000",
            year=2026,
            is_regulated=False,
            house_count=1,
        )
        ltv = Decimal(result["ltv"])
        assert abs(ltv - Decimal("0.70")) < Decimal("0.0001")
        assert result["within_cap"] is True

    def test_ltv_non_regulated_multi_house(self) -> None:
        """Non-regulated, 2 houses, 60% cap."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="600000000",
            property_value="1000000000",
            year=2026,
            is_regulated=False,
            house_count=2,
        )
        assert result["within_cap"] is True

    def test_ltv_trace_present(self) -> None:
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="300000000",
            property_value="600000000",
            year=2026,
            is_regulated=True,
            house_count=1,
        )
        assert "trace" in result


class TestDTI:
    def test_dti_non_regulated(self) -> None:
        """monthly_debt=2M, income=5M, non-regulated -> dti=0.40, within cap (60%)."""
        result = REGISTRY.invoke(
            "realestate.kr_dti",
            monthly_debt_payment="2000000",
            monthly_income="5000000",
            year=2026,
            is_regulated=False,
        )
        dti = Decimal(result["dti"])
        assert abs(dti - Decimal("0.40")) < Decimal("0.0001")
        assert result["within_cap"] is True

    def test_dti_regulated_over_cap(self) -> None:
        """monthly_debt=3M, income=5M, regulated -> dti=0.60, cap=0.40, within_cap=False."""
        result = REGISTRY.invoke(
            "realestate.kr_dti",
            monthly_debt_payment="3000000",
            monthly_income="5000000",
            year=2026,
            is_regulated=True,
        )
        dti = Decimal(result["dti"])
        assert dti > Decimal("0.40")
        assert result["within_cap"] is False

    def test_dti_policy_version(self) -> None:
        result = REGISTRY.invoke(
            "realestate.kr_dti",
            monthly_debt_payment="2000000",
            monthly_income="5000000",
            year=2026,
            is_regulated=False,
        )
        assert "policy_version" in result

    def test_realestate_unsupported_year(self) -> None:
        """year=2099 -> UnsupportedPolicyError."""
        with pytest.raises(UnsupportedPolicyError):
            REGISTRY.invoke(
                "realestate.kr_dti",
                monthly_debt_payment="2000000",
                monthly_income="5000000",
                year=2099,
                is_regulated=False,
            )
