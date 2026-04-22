"""Tests for finance Black-Scholes option pricer."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.finance  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestBlackScholes:
    def test_black_scholes_call_atm_textbook(self) -> None:
        """S=K=100, T=1, r=0.05, sigma=0.2, q=0 -> call ~ 10.4506, delta ~ 0.6368."""
        result = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="call",
            dividend_yield="0",
        )
        price = Decimal(result["price"])
        delta = Decimal(result["delta"])
        assert abs(price - Decimal("10.4506")) < Decimal("0.0005")
        assert abs(delta - Decimal("0.6368")) < Decimal("0.0005")
        assert "trace" in result

    def test_black_scholes_put_atm(self) -> None:
        """S=K=100, T=1, r=0.05, sigma=0.2, q=0 -> put ~ 5.5735."""
        result = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="put",
            dividend_yield="0",
        )
        price = Decimal(result["price"])
        assert abs(price - Decimal("5.5735")) < Decimal("0.0005")

    def test_black_scholes_put_call_parity(self) -> None:
        """call + K*exp(-rT) = put + S (put-call parity)."""
        import mpmath as mp
        params = dict(
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            dividend_yield="0",
        )
        call_result = REGISTRY.invoke("finance.black_scholes", option_type="call", **params)
        put_result  = REGISTRY.invoke("finance.black_scholes", option_type="put",  **params)

        call_price = Decimal(call_result["price"])
        put_price  = Decimal(put_result["price"])
        K   = Decimal("100")
        S   = Decimal("100")
        r   = Decimal("0.05")
        T   = Decimal("1")

        # K * exp(-rT) using mpmath for precision
        disc = Decimal(str(mp.exp(-float(r * T))))
        lhs = call_price + K * disc
        rhs = put_price + S
        assert abs(lhs - rhs) < Decimal("0.001")

    def test_black_scholes_greeks_present(self) -> None:
        """All Greeks must be present in result."""
        result = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="call",
        )
        for greek in ("price", "delta", "gamma", "vega", "theta", "rho"):
            assert greek in result
            Decimal(result[greek])  # parseable as Decimal

    def test_black_scholes_call_delta_in_range(self) -> None:
        """Call delta must be in (0, 1)."""
        result = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="call",
        )
        delta = Decimal(result["delta"])
        assert Decimal("0") < delta < Decimal("1")

    def test_black_scholes_put_delta_in_range(self) -> None:
        """Put delta must be in (-1, 0)."""
        result = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="put",
        )
        delta = Decimal(result["delta"])
        assert Decimal("-1") < delta < Decimal("0")

    def test_black_scholes_deep_itm_call_delta_near_1(self) -> None:
        """Deep ITM call: delta ~ 1."""
        result = REGISTRY.invoke(
            "finance.black_scholes",
            spot="200",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="call",
        )
        delta = Decimal(result["delta"])
        assert delta > Decimal("0.95")

    def test_black_scholes_invalid_option_type_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.black_scholes",
                spot="100",
                strike="100",
                time_to_expiry="1",
                rate="0.05",
                sigma="0.2",
                option_type="american",
            )

    def test_black_scholes_negative_spot_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.black_scholes",
                spot="-100",
                strike="100",
                time_to_expiry="1",
                rate="0.05",
                sigma="0.2",
                option_type="call",
            )

    def test_black_scholes_zero_expiry_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.black_scholes",
                spot="100",
                strike="100",
                time_to_expiry="0",
                rate="0.05",
                sigma="0.2",
                option_type="call",
            )

    def test_black_scholes_zero_sigma_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "finance.black_scholes",
                spot="100",
                strike="100",
                time_to_expiry="1",
                rate="0.05",
                sigma="0",
                option_type="call",
            )

    def test_black_scholes_with_dividend(self) -> None:
        """With positive dividend yield, call price < no-dividend call."""
        no_div = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="call",
            dividend_yield="0",
        )
        with_div = REGISTRY.invoke(
            "finance.black_scholes",
            spot="100",
            strike="100",
            time_to_expiry="1",
            rate="0.05",
            sigma="0.2",
            option_type="call",
            dividend_yield="0.03",
        )
        assert Decimal(with_div["price"]) < Decimal(no_div["price"])

    def test_black_scholes_gamma_positive(self) -> None:
        """Gamma is always positive for both call and put."""
        for opt_type in ("call", "put"):
            result = REGISTRY.invoke(
                "finance.black_scholes",
                spot="100",
                strike="100",
                time_to_expiry="1",
                rate="0.05",
                sigma="0.2",
                option_type=opt_type,
            )
            assert Decimal(result["gamma"]) > 0
