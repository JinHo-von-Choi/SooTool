"""Tests for engineering.control tools (Tier 2)."""
from __future__ import annotations

import concurrent.futures
import math
from decimal import Decimal

import pytest

import sootool.modules.engineering  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _assert_close(actual: str, expected: Decimal, tol: Decimal = Decimal("1E-6")) -> None:
    assert abs(Decimal(actual) - expected) <= tol, f"{actual} != {expected} (tol {tol})"


class TestFirstOrderResponse:
    def test_steady_state(self) -> None:
        """t → ∞  →  y → K·u = 5.0."""
        r = REGISTRY.invoke(
            "engineering.first_order_response",
            gain="2", time_constant="1", input_step="2.5", time="50",
        )
        _assert_close(r["response"], Decimal("5"), tol=Decimal("1E-15"))
        assert Decimal(r["steady_state"]) == Decimal("5")

    def test_time_zero(self) -> None:
        """t = 0 → y = 0."""
        r = REGISTRY.invoke(
            "engineering.first_order_response",
            gain="2", time_constant="1", input_step="2.5", time="0",
        )
        assert Decimal(r["response"]) == Decimal("0")

    def test_one_time_constant(self) -> None:
        """t = τ → y = K·u·(1 − 1/e) ≈ 0.6321 K u."""
        r = REGISTRY.invoke(
            "engineering.first_order_response",
            gain="1", time_constant="2", input_step="1", time="2",
        )
        expected = Decimal(str(1 - math.exp(-1)))
        _assert_close(r["response"], expected, tol=Decimal("1E-10"))

    def test_zero_tau_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.first_order_response",
                gain="1", time_constant="0", input_step="1", time="1",
            )

    def test_negative_time_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.first_order_response",
                gain="1", time_constant="1", input_step="1", time="-1",
            )


class TestSecondOrderResponse:
    def test_underdamped(self) -> None:
        """ζ=0.5, ωn=10 → ωd = 10·√0.75 ≈ 8.6603, Mp = exp(−π·0.5/√0.75) ≈ 0.16303."""
        r = REGISTRY.invoke(
            "engineering.second_order_response",
            damping_ratio="0.5", natural_freq="10",
        )
        _assert_close(r["damped_freq"], Decimal(str(10 * math.sqrt(0.75))), tol=Decimal("1E-10"))
        _assert_close(
            r["overshoot"],
            Decimal(str(math.exp(-math.pi * 0.5 / math.sqrt(0.75)))),
            tol=Decimal("1E-10"),
        )
        assert r["regime"] == "underdamped"
        _assert_close(r["settling_time"], Decimal("0.8"), tol=Decimal("1E-15"))

    def test_critically_damped(self) -> None:
        r = REGISTRY.invoke(
            "engineering.second_order_response",
            damping_ratio="1", natural_freq="5",
        )
        assert r["regime"] == "critically_damped"
        assert Decimal(r["overshoot"]) == Decimal("0")
        assert Decimal(r["damped_freq"]) == Decimal("0")

    def test_overdamped(self) -> None:
        r = REGISTRY.invoke(
            "engineering.second_order_response",
            damping_ratio="1.5", natural_freq="5",
        )
        assert r["regime"] == "overdamped"

    def test_zero_damping_undefined_settling(self) -> None:
        r = REGISTRY.invoke(
            "engineering.second_order_response",
            damping_ratio="0", natural_freq="1",
        )
        assert r["settling_time"] == "Infinity"

    def test_negative_damping_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.second_order_response",
                damping_ratio="-0.1", natural_freq="1",
            )


class TestBodeMagnitudePhase:
    def test_pole_at_corner(self) -> None:
        """ω = ωc → |G| = 1/√2 → −3.0103 dB, phase = −45°."""
        r = REGISTRY.invoke(
            "engineering.bode_magnitude_phase",
            mode="pole", corner_freq="100", frequency="100",
        )
        _assert_close(r["magnitude_db"], Decimal(str(-3.0102999566)), tol=Decimal("1E-6"))
        _assert_close(r["phase_deg"], Decimal("-45"), tol=Decimal("1E-8"))

    def test_zero_at_corner(self) -> None:
        r = REGISTRY.invoke(
            "engineering.bode_magnitude_phase",
            mode="zero", corner_freq="100", frequency="100",
        )
        _assert_close(r["magnitude_db"], Decimal(str(3.0102999566)), tol=Decimal("1E-6"))
        _assert_close(r["phase_deg"], Decimal("45"), tol=Decimal("1E-8"))

    def test_pole_far_below_corner(self) -> None:
        """ω << ωc → |G| ≈ 0 dB."""
        r = REGISTRY.invoke(
            "engineering.bode_magnitude_phase",
            mode="pole", corner_freq="1000", frequency="1",
        )
        _assert_close(r["magnitude_db"], Decimal("0"), tol=Decimal("1E-4"))

    def test_zero_frequency_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bode_magnitude_phase",
                mode="pole", corner_freq="1", frequency="0",
            )

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.bode_magnitude_phase",
                mode="integrator", corner_freq="1", frequency="1",
            )


class TestPidDiscreteOutput:
    def test_proportional_only(self) -> None:
        """kp=2, e=3, prev_e=1 → Δu = 2·2 = 4, u = u_prev + 4."""
        r = REGISTRY.invoke(
            "engineering.pid_discrete_output",
            kp="2", ki="0", kd="0", sample_time="0.1",
            error_curr="3", error_prev="1", error_prev2="0",
            output_prev="10",
        )
        assert Decimal(r["output"]) == Decimal("14")
        assert Decimal(r["p_term"]) == Decimal("4")
        assert Decimal(r["i_term"]) == Decimal("0")
        assert Decimal(r["d_term"]) == Decimal("0")

    def test_integral_only(self) -> None:
        """ki=0.5, e=4, Ts=0.1 → i_term = 0.5·4·0.1 = 0.2."""
        r = REGISTRY.invoke(
            "engineering.pid_discrete_output",
            kp="0", ki="0.5", kd="0", sample_time="0.1",
            error_curr="4", error_prev="4", error_prev2="4",
            output_prev="0",
        )
        assert Decimal(r["i_term"]) == Decimal("0.2")
        assert Decimal(r["output"]) == Decimal("0.2")

    def test_derivative_term(self) -> None:
        """kd=1, Δe=1-0=1, Δe_prev=0-0=0, Ts=0.1 → d_term = 1·1/0.1 = 10."""
        r = REGISTRY.invoke(
            "engineering.pid_discrete_output",
            kp="0", ki="0", kd="1", sample_time="0.1",
            error_curr="1", error_prev="0", error_prev2="0",
            output_prev="0",
        )
        assert Decimal(r["d_term"]) == Decimal("10")

    def test_zero_ts_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "engineering.pid_discrete_output",
                kp="1", ki="1", kd="1", sample_time="0",
                error_curr="1", error_prev="0", error_prev2="0",
                output_prev="0",
            )


class TestConcurrency:
    def test_first_order_batch_race_free(self) -> None:
        """engineering.first_order_response must remain race-free under N=100."""
        def _call(n: int) -> dict:
            return REGISTRY.invoke(
                "engineering.first_order_response",
                gain="1", time_constant="1",
                input_step=str(n), time="100",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_call, n) for n in range(1, 101)]
            results = [f.result() for f in futures]

        for n, res in enumerate(results, start=1):
            _assert_close(res["response"], Decimal(n), tol=Decimal("1E-20"))
