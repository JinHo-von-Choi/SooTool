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

    def test_dsr_nonbank_cap_50(self) -> None:
        """2금융권 DSR 50%: 45%는 은행권 한도 초과, 2금융권 한도 이내."""
        bank = REGISTRY.invoke(
            "realestate.kr_dsr", annual_debt_payment="4500000", annual_income="10000000", year=2026,
        )
        nonbank = REGISTRY.invoke(
            "realestate.kr_dsr", annual_debt_payment="4500000", annual_income="10000000", year=2026,
            is_nonbank=True,
        )
        assert bank["within_cap"] is False
        assert nonbank["within_cap"] is True
        assert Decimal(nonbank["cap"]) == Decimal("0.50")

    def test_dsr_stress_rate_floor(self) -> None:
        """수도권·규제지역 주담대 스트레스 금리 하한 3%, 지방 0.75%."""
        capital = REGISTRY.invoke(
            "realestate.kr_dsr", annual_debt_payment="3000000", annual_income="10000000", year=2026,
            mortgage_region="capital_or_regulated",
        )
        other = REGISTRY.invoke(
            "realestate.kr_dsr", annual_debt_payment="3000000", annual_income="10000000", year=2026,
            mortgage_region="non_capital",
        )
        plain = REGISTRY.invoke(
            "realestate.kr_dsr", annual_debt_payment="3000000", annual_income="10000000", year=2026,
        )
        assert Decimal(capital["stress_rate_floor"]) == Decimal("0.03")
        assert Decimal(other["stress_rate_floor"]) == Decimal("0.0075")
        assert plain["stress_rate_floor"] is None

    def test_dsr_invalid_region_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "realestate.kr_dsr", annual_debt_payment="1", annual_income="10", year=2026,
                mortgage_region="seoul",
            )

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
        """규제지역 LTV 40%(2025-09-08 행정지도): 3억/6억 = 50% 초과, 한도 2.4억."""
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
        assert result["within_cap"] is False
        assert Decimal(result["cap_rate"]) == Decimal("0.40")
        assert Decimal(result["max_loan"]) == Decimal("240000000")

    def test_ltv_regulated_at_40_percent(self) -> None:
        """2.4억/6억 = 40% → 한도 이내."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="240000000",
            property_value="600000000",
            year=2026,
            is_regulated=True,
            house_count=1,
        )
        assert result["within_cap"] is True

    def test_ltv_price_based_amount_cap(self) -> None:
        """규제지역 시가 20억: 40% = 8억이지만 15억 초과 25억 이하 한도 4억."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="500000000",
            property_value="2000000000",
            year=2026,
            is_regulated=True,
            house_count=1,
        )
        assert Decimal(result["amount_cap"]) == Decimal("400000000")
        assert Decimal(result["max_loan"]) == Decimal("400000000")
        assert result["within_cap"] is False

    def test_ltv_price_cap_boundaries(self) -> None:
        """시가 15억 이하 6억, 25억 초과 2억."""
        at_15 = REGISTRY.invoke(
            "realestate.kr_ltv", loan_amount="0", property_value="1500000000",
            year=2026, is_regulated=True, house_count=1,
        )
        assert Decimal(at_15["max_loan"]) == Decimal("600000000")
        over_25 = REGISTRY.invoke(
            "realestate.kr_ltv", loan_amount="0", property_value="3000000000",
            year=2026, is_regulated=True, house_count=1,
        )
        assert Decimal(over_25["max_loan"]) == Decimal("200000000")

    def test_ltv_capital_non_regulated_multi_house_blocked(self) -> None:
        """수도권 비규제지역 2주택 이상 추가구입 주담대 금지."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="1",
            property_value="600000000",
            year=2026,
            is_regulated=False,
            house_count=2,
            is_capital_area=True,
        )
        assert result["max_loan"] == "0"
        assert result["within_cap"] is False

    def test_ltv_first_time_buyer_capital(self) -> None:
        """수도권 생애최초 70%, 시가 10억: 7억이지만 가격별 한도·생애최초 한도 6억."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="600000000",
            property_value="1000000000",
            year=2026,
            is_regulated=False,
            house_count=1,
            is_capital_area=True,
            is_first_time_buyer=True,
        )
        assert Decimal(result["cap_rate"]) == Decimal("0.70")
        assert Decimal(result["max_loan"]) == Decimal("600000000")
        assert result["within_cap"] is True

    def test_ltv_first_time_buyer_non_capital(self) -> None:
        """비수도권 비규제 생애최초 80%, 시가 5억 → 4억."""
        result = REGISTRY.invoke(
            "realestate.kr_ltv",
            loan_amount="400000000",
            property_value="500000000",
            year=2026,
            is_regulated=False,
            house_count=1,
            is_first_time_buyer=True,
        )
        assert Decimal(result["cap_rate"]) == Decimal("0.80")
        assert Decimal(result["max_loan"]) == Decimal("400000000")
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
        """monthly_debt=2M, income=5M, non-regulated -> dti=0.40, within cap."""
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

    def test_dti_capital_non_regulated_cap(self) -> None:
        """규제지역 외 수도권 60%: 0.65 → 초과."""
        result = REGISTRY.invoke(
            "realestate.kr_dti",
            monthly_debt_payment="3250000",
            monthly_income="5000000",
            year=2026,
            is_regulated=False,
            is_capital_area=True,
        )
        assert Decimal(result["cap"]) == Decimal("0.60")
        assert result["within_cap"] is False

    def test_dti_non_capital_no_cap(self) -> None:
        """수도권 외 비규제지역은 DTI 한도 없음(은행업감독규정 별표6 3.가)."""
        result = REGISTRY.invoke(
            "realestate.kr_dti",
            monthly_debt_payment="4000000",
            monthly_income="5000000",
            year=2026,
            is_regulated=False,
        )
        assert result["cap"] is None
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
