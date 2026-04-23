"""Control systems engineering tools (Tier 2).

Tools:
  - first_order_response  : 1차 시스템 y(t) = K·(1 − exp(−t/τ))·u
  - second_order_response : 2차 시스템 ωn, ζ, overshoot, settling time
  - bode_magnitude_phase  : 1극·1영 전달함수의 Bode 크기·위상
  - pid_discrete_output   : 이산 PID 제어기 출력 u_k = u_{k-1} + Δu

ADR-001 Decimal, ADR-003 trace, ADR-007 stateless.
exp·log·sqrt·atan 등 초월함수는 mpmath workdps(50) → mpmath_to_decimal(digits=30).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_TWO     = Decimal("2")
_MP_DPS  = 50
_OUT_DIG = 30


def _exp_mp(x: Decimal) -> Decimal:
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.exp(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _ln_mp(x: Decimal) -> Decimal:
    if x <= _ZERO:
        raise InvalidInputError("로그의 인수는 0 초과여야 합니다.")
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.log(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _sqrt_mp(x: Decimal) -> Decimal:
    if x < _ZERO:
        raise InvalidInputError("제곱근의 피연산자는 0 이상이어야 합니다.")
    if x == _ZERO:
        return _ZERO
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.sqrt(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _pi_dec() -> Decimal:
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.pi, digits=_OUT_DIG)


# ---------------------------------------------------------------------------
# First-order system
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="first_order_response",
    description=(
        "1차 시스템 스텝 응답. G(s) = K / (τ s + 1). "
        "y(t) = K·u·(1 − exp(−t/τ)). "
        "반환: 응답값·정상상태(K·u)·시정수."
    ),
    version="1.0.0",
)
def first_order_response(
    gain:           str,
    time_constant:  str,
    input_step:     str,
    time:           str,
) -> dict[str, Any]:
    """First-order step response y(t)."""
    trace = CalcTrace(
        tool="engineering.first_order_response",
        formula="y(t) = K·u·(1 − exp(−t/τ))",
    )
    k_d = D(gain)
    tau_d = D(time_constant)
    u_d = D(input_step)
    t_d = D(time)
    if tau_d <= _ZERO:
        raise InvalidInputError("time_constant는 0 초과여야 합니다.")
    if t_d < _ZERO:
        raise InvalidInputError("time은 0 이상이어야 합니다.")

    trace.input("gain",          gain)
    trace.input("time_constant", time_constant)
    trace.input("input_step",    input_step)
    trace.input("time",          time)

    neg_ratio = -div(t_d, tau_d)
    decay = _exp_mp(neg_ratio)
    factor = _ONE - decay
    response = mul(mul(k_d, u_d), factor)
    steady = mul(k_d, u_d)

    trace.step("exp_term", str(decay))
    trace.step("response", str(response))
    trace.step("steady_state", str(steady))
    trace.output({"response": str(response), "steady_state": str(steady)})

    return {
        "response":      str(response),
        "steady_state":  str(steady),
        "time_constant": str(tau_d),
        "trace":         trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Second-order system
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="second_order_response",
    description=(
        "2차 시스템 특성. G(s) = ωn² / (s² + 2ζωn s + ωn²). "
        "ζ, ωn 입력 → damped_freq ωd = ωn·√(1−ζ²), "
        "overshoot = exp(−π ζ / √(1−ζ²)) (ζ<1), "
        "settling_time ≈ 4 / (ζ ωn) (2% 기준)."
    ),
    version="1.0.0",
)
def second_order_response(
    damping_ratio:    str,
    natural_freq:     str,
) -> dict[str, Any]:
    """Compute canonical second-order system metrics."""
    trace = CalcTrace(
        tool="engineering.second_order_response",
        formula="ωd = ωn √(1−ζ²); Mp = exp(−π ζ / √(1−ζ²)); ts ≈ 4/(ζ ωn)",
    )
    zeta_d = D(damping_ratio)
    wn_d = D(natural_freq)
    if zeta_d < _ZERO:
        raise InvalidInputError("damping_ratio는 0 이상이어야 합니다.")
    if wn_d <= _ZERO:
        raise InvalidInputError("natural_freq는 0 초과여야 합니다.")

    trace.input("damping_ratio", damping_ratio)
    trace.input("natural_freq",  natural_freq)

    one_minus_zeta_sq = _ONE - mul(zeta_d, zeta_d)
    if one_minus_zeta_sq > _ZERO:
        sqrt_term = _sqrt_mp(one_minus_zeta_sq)
        damped_freq = mul(wn_d, sqrt_term)
        if zeta_d == _ZERO:
            overshoot = _ONE
        else:
            exponent = div(mul(-_pi_dec(), zeta_d), sqrt_term)
            overshoot = _exp_mp(exponent)
        regime = "underdamped"
    elif one_minus_zeta_sq == _ZERO:
        damped_freq = _ZERO
        overshoot = _ZERO
        regime = "critically_damped"
    else:
        damped_freq = _ZERO
        overshoot = _ZERO
        regime = "overdamped"

    if zeta_d > _ZERO:
        settling_time = div(Decimal("4"), mul(zeta_d, wn_d))
    else:
        settling_time = Decimal("Infinity")

    trace.step("damped_freq",   str(damped_freq))
    trace.step("overshoot",     str(overshoot))
    trace.step("settling_time", str(settling_time))
    trace.step("regime",        regime)
    trace.output({
        "damped_freq":   str(damped_freq),
        "overshoot":     str(overshoot),
        "settling_time": str(settling_time),
        "regime":        regime,
    })

    return {
        "damped_freq":    str(damped_freq),
        "overshoot":      str(overshoot),
        "settling_time":  str(settling_time),
        "regime":         regime,
        "trace":          trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Bode magnitude / phase
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="bode_magnitude_phase",
    description=(
        "1차 전달함수 Bode 크기(dB)·위상(deg). "
        "mode='pole': G(jω) = 1 / (1 + jω/ωc). "
        "mode='zero': G(jω) = 1 + jω/ωc. "
        "magnitude_db = 20 log10|G|, phase = arg(G)."
    ),
    version="1.0.0",
)
def bode_magnitude_phase(
    mode:            str,
    corner_freq:     str,
    frequency:       str,
) -> dict[str, Any]:
    """Compute Bode magnitude (dB) and phase (deg) for a single pole or zero."""
    trace = CalcTrace(tool="engineering.bode_magnitude_phase", formula="")
    if mode not in ("pole", "zero"):
        raise InvalidInputError("mode는 'pole' 또는 'zero'여야 합니다.")
    wc_d = D(corner_freq)
    w_d = D(frequency)
    if wc_d <= _ZERO:
        raise InvalidInputError("corner_freq는 0 초과여야 합니다.")
    if w_d <= _ZERO:
        raise InvalidInputError("frequency는 0 초과여야 합니다.")

    trace.input("mode",        mode)
    trace.input("corner_freq", corner_freq)
    trace.input("frequency",   frequency)

    ratio = div(w_d, wc_d)
    with mpmath.workdps(_MP_DPS):
        r_mp = mpmath.mpf(str(ratio))
        magnitude_abs_mp = mpmath.sqrt(mpmath.mpf("1") + r_mp * r_mp)
        mag_db_mp = mpmath.mpf("20") * mpmath.log10(magnitude_abs_mp)
        phase_rad_mp = mpmath.atan(r_mp)
        phase_deg_mp = phase_rad_mp * mpmath.mpf("180") / mpmath.pi
        if mode == "pole":
            mag_db_mp = -mag_db_mp
            phase_deg_mp = -phase_deg_mp
            trace.formula = "G(jω)=1/(1+jω/ωc)"
        else:
            trace.formula = "G(jω)=1+jω/ωc"
        mag_db = mpmath_to_decimal(mag_db_mp, digits=_OUT_DIG)
        phase_deg = mpmath_to_decimal(phase_deg_mp, digits=_OUT_DIG)

    trace.step("magnitude_db", str(mag_db))
    trace.step("phase_deg",    str(phase_deg))
    trace.output({"magnitude_db": str(mag_db), "phase_deg": str(phase_deg)})

    return {
        "magnitude_db": str(mag_db),
        "phase_deg":    str(phase_deg),
        "trace":        trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Discrete PID
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="pid_discrete_output",
    description=(
        "이산 PID (velocity form). Δu = Kp·Δe + Ki·e·Ts + Kd·(Δe − Δe_prev)/Ts. "
        "입력: kp, ki, kd, sample_time Ts, error_curr, error_prev, error_prev2, "
        "output_prev. 반환: output, delta_u, 항별 기여도."
    ),
    version="1.0.0",
)
def pid_discrete_output(
    kp:           str,
    ki:           str,
    kd:           str,
    sample_time:  str,
    error_curr:   str,
    error_prev:   str,
    error_prev2:  str,
    output_prev:  str,
) -> dict[str, Any]:
    """Velocity-form discrete PID — returns the new output u_k."""
    trace = CalcTrace(
        tool="engineering.pid_discrete_output",
        formula="u_k = u_{k-1} + Kp Δe + Ki e Ts + Kd (Δe − Δe_prev)/Ts",
    )
    kp_d = D(kp)
    ki_d = D(ki)
    kd_d = D(kd)
    ts_d = D(sample_time)
    e0 = D(error_curr)
    e1 = D(error_prev)
    e2 = D(error_prev2)
    u_prev = D(output_prev)
    if ts_d <= _ZERO:
        raise InvalidInputError("sample_time은 0 초과여야 합니다.")

    trace.input("kp",           kp)
    trace.input("ki",           ki)
    trace.input("kd",           kd)
    trace.input("sample_time",  sample_time)
    trace.input("error_curr",   error_curr)
    trace.input("error_prev",   error_prev)
    trace.input("error_prev2",  error_prev2)
    trace.input("output_prev",  output_prev)

    delta_e      = e0 - e1
    delta_e_prev = e1 - e2

    p_term = mul(kp_d, delta_e)
    i_term = mul(ki_d, mul(e0, ts_d))
    d_term = div(mul(kd_d, delta_e - delta_e_prev), ts_d)

    delta_u = p_term + i_term + d_term
    output = u_prev + delta_u

    trace.step("p_term",  str(p_term))
    trace.step("i_term",  str(i_term))
    trace.step("d_term",  str(d_term))
    trace.step("delta_u", str(delta_u))
    trace.step("output",  str(output))
    trace.output({"output": str(output), "delta_u": str(delta_u)})

    return {
        "output":  str(output),
        "delta_u": str(delta_u),
        "p_term":  str(p_term),
        "i_term":  str(i_term),
        "d_term":  str(d_term),
        "trace":   trace.to_dict(),
    }
