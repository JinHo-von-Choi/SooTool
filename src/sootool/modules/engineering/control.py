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

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

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
class FirstOrderResponseResult(TracedResult):
    """1차 시스템 스텝 응답. 값은 모두 Decimal 문자열."""

    response:      str
    steady_state:  str
    time_constant: str


@REGISTRY.tool(
    namespace="engineering",
    name="first_order_response",
    description=(
        "1차 시스템 G(s)=K/(τs+1)의 스텝 응답 y(t)=K·u·(1−exp(−t/τ))를 구한다. "
        "gain K, time_constant τ(초, 0 초과), input_step u, time t(초, 0 이상)는 Decimal 문자열. "
        "지수항은 유효숫자 30자리. 반환: response, steady_state(K·u), time_constant. "
        "오용 주의: 2차 이상 시스템이나 임펄스 응답에는 쓸 수 없다."
    ),
    version="1.0.0",
)
def first_order_response(
    gain:           str,
    time_constant:  str,
    input_step:     str,
    time:           str,
) -> FirstOrderResponseResult:
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
class SecondOrderResponseResult(TracedResult):
    """2차 시스템 특성. 값은 Decimal 문자열이며 settling_time 은 ζ=0 이면 "Infinity"."""

    damped_freq:   str
    overshoot:     str
    settling_time: str
    regime:        str


@REGISTRY.tool(
    namespace="engineering",
    name="second_order_response",
    description=(
        "2차 시스템 G(s)=ωn²/(s²+2ζωn·s+ωn²)의 감쇠 고유진동수 ωd, 최대 오버슈트, 정착시간을 구한다. "
        "damping_ratio ζ(0 이상)와 natural_freq ωn(rad/s, 0 초과)은 Decimal 문자열. "
        "overshoot 는 비율(0~1, 백분율 아님)이고 ζ≥1 이면 0, ζ=0 이면 1. "
        "settling_time=4/(ζωn)은 2% 기준 근사이며 ζ=0 이면 \"Infinity\". "
        "regime: underdamped, critically_damped, overdamped. 초월함수는 유효숫자 30자리."
    ),
    version="1.0.0",
)
def second_order_response(
    damping_ratio:    str,
    natural_freq:     str,
) -> SecondOrderResponseResult:
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
class BodeMagnitudePhaseResult(TracedResult):
    """Bode 크기(dB)와 위상(도). 값은 Decimal 문자열."""

    magnitude_db: str
    phase_deg:    str


@REGISTRY.tool(
    namespace="engineering",
    name="bode_magnitude_phase",
    description=(
        "단일 극점 또는 영점 1차 전달함수의 Bode 크기(dB)와 위상(도)을 구한다. "
        "mode='pole'이면 G(jω)=1/(1+jω/ωc), 'zero'이면 G(jω)=1+jω/ωc. "
        "corner_freq ωc와 frequency ω는 같은 단위(rad/s 또는 Hz)의 0 초과 Decimal 문자열이며 "
        "비율만 쓴다. 유효숫자 30자리. 오용 주의: 극점과 영점이 여러 개인 전달함수는 직접 합산해야 한다."
    ),
    version="1.0.0",
)
def bode_magnitude_phase(
    mode:            str,
    corner_freq:     str,
    frequency:       str,
) -> BodeMagnitudePhaseResult:
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
class PidDiscreteOutputResult(TracedResult):
    """이산 PID 출력과 항별 기여도. 값은 Decimal 문자열."""

    output:  str
    delta_u: str
    p_term:  str
    i_term:  str
    d_term:  str


@REGISTRY.tool(
    namespace="engineering",
    name="pid_discrete_output",
    description=(
        "속도형(velocity form) 이산 PID의 새 출력 u_k=u_{k-1}+Δu를 구한다. "
        "Δu=Kp·Δe+Ki·e·Ts+Kd·(Δe−Δe_prev)/Ts. kp, ki, kd, sample_time Ts(0 초과), "
        "error_curr, error_prev, error_prev2, output_prev 는 Decimal 문자열. "
        "반환: output, delta_u, p_term, i_term, d_term. 적분항은 현재 오차 e에 Ts를 곱하는 방식이며 "
        "출력 포화와 anti-windup은 없다."
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
) -> PidDiscreteOutputResult:
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
