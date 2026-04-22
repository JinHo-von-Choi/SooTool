"""Tests for real estate transfer tax adapter."""
from __future__ import annotations

from decimal import Decimal

import sootool.modules.realestate  # noqa: F401
import sootool.modules.tax  # noqa: F401  — registers tax.capital_gains_kr
from sootool.core.registry import REGISTRY


class TestTransferTax:
    def test_transfer_tax_delegate_returns_consistent(self) -> None:
        """realestate.kr_transfer_tax result is consistent with tax.capital_gains_kr."""
        common_args = dict(
            acquisition_price="300000000",
            sale_price="500000000",
            holding_years=5,
            is_one_house=True,
            year=2026,
        )
        realestate_result = REGISTRY.invoke("realestate.kr_transfer_tax", **common_args)
        tax_result        = REGISTRY.invoke("tax.capital_gains_kr",        **common_args)

        # Core financial fields must match
        assert realestate_result["gain"]         == tax_result["gain"]
        assert realestate_result["tax"]          == tax_result["tax"]
        assert realestate_result["taxable_gain"] == tax_result["taxable_gain"]

    def test_transfer_tax_domain_metadata(self) -> None:
        """realestate adapter adds domain and module fields."""
        result = REGISTRY.invoke(
            "realestate.kr_transfer_tax",
            acquisition_price="300000000",
            sale_price="500000000",
            holding_years=3,
            is_one_house=False,
            year=2026,
        )
        assert result["domain"] == "realestate"
        assert result["module"] == "realestate.kr_transfer_tax"

    def test_transfer_tax_no_gain(self) -> None:
        """Sale at loss -> tax=0."""
        result = REGISTRY.invoke(
            "realestate.kr_transfer_tax",
            acquisition_price="500000000",
            sale_price="300000000",
            holding_years=2,
            is_one_house=False,
            year=2026,
        )
        assert result["tax"] == "0"

    def test_transfer_tax_one_house_ltct(self) -> None:
        """1세대1주택 10년 이상 -> LTCT 80% 공제 -> 세금 대폭 감소."""
        result = REGISTRY.invoke(
            "realestate.kr_transfer_tax",
            acquisition_price="100000000",
            sale_price="500000000",
            holding_years=10,
            is_one_house=True,
            year=2026,
        )
        # Gain = 400M, LTCT 80% = 320M deduction, taxable = 80M
        taxable = Decimal(result["taxable_gain"])
        assert taxable < Decimal("400000000")

    def test_transfer_tax_trace_present(self) -> None:
        result = REGISTRY.invoke(
            "realestate.kr_transfer_tax",
            acquisition_price="300000000",
            sale_price="500000000",
            holding_years=3,
            is_one_house=False,
            year=2026,
        )
        assert "trace" in result
        assert "policy_version" in result
