"""AC impedance, time constants, resonance and RC filter tools.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.engineering.electrical_ac._common import (
    _ONE,
    _TWO,
    _ZERO,
    _atan2_deg_mp,
    _pi_dec,
    _sqrt_mp,
)


def _impedance_rlc_series(
    r: Decimal, ind: Decimal, c: Decimal, omega: Decimal
) -> tuple[Decimal, Decimal]:
    """Series R-L-C impedance → (Z_real, Z_imag).

    Z = R + j(ωL - 1/(ωC)).
    Pass C == 0 to skip capacitor term, L == 0 to skip inductor term.
    """
    xl = mul(omega, ind) if ind > _ZERO else _ZERO
    xc = div(_ONE, mul(omega, c)) if c > _ZERO else _ZERO
    return r, xl - xc


@REGISTRY.tool(
    namespace="engineering",
    name="ac_impedance",
    description=(
        "AC 회로의 R/L/C 임피던스 크기 및 위상각 계산. "
        "topology는 'series' 또는 'parallel'."
    ),
    version="1.0.0",
)
def ac_impedance(
    frequency: str,
    resistance:  str = "0",
    inductance:  str = "0",
    capacitance: str = "0",
    topology:    str = "series",
) -> dict[str, Any]:
    """Compute AC impedance magnitude and phase for an R-L-C combination.

    Series:   Z = R + j(ωL - 1/(ωC))
    Parallel: Y = 1/R + 1/(jωL) + jωC → Z = 1/Y (closed-form).

    Args:
        frequency:   주파수 f (Hz, > 0)
        resistance:  저항 R (Ω, ≥ 0)
        inductance:  인덕턴스 L (H, ≥ 0)
        capacitance: 커패시턴스 C (F, ≥ 0)
        topology:    "series" | "parallel"

    Returns:
        {magnitude, phase_deg, real, imag, trace}
    """
    trace = CalcTrace(
        tool="engineering.ac_impedance",
        formula="Z = R + j(ωL - 1/(ωC)) (series); Y = 1/R + 1/(jωL) + jωC (parallel)",
    )

    f_d = D(frequency)
    r_d = D(resistance)
    l_d = D(inductance)
    c_d = D(capacitance)

    if f_d <= _ZERO:
        raise InvalidInputError("frequency는 0 초과여야 합니다.")
    for name, val in [("resistance", r_d), ("inductance", l_d), ("capacitance", c_d)]:
        if val < _ZERO:
            raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    if topology not in ("series", "parallel"):
        raise InvalidInputError("topology는 'series' 또는 'parallel'이어야 합니다.")

    trace.input("frequency",   frequency)
    trace.input("resistance",  resistance)
    trace.input("inductance",  inductance)
    trace.input("capacitance", capacitance)
    trace.input("topology",    topology)

    omega = mul(mul(_TWO, _pi_dec()), f_d)
    trace.step("omega", str(omega))

    if topology == "series":
        z_real, z_imag = _impedance_rlc_series(r_d, l_d, c_d, omega)
    else:
        # Parallel: compose admittances Y_R, Y_L (jωL → -j/(ωL)), Y_C (jωC).
        # Z_total = 1 / (Y_R + Y_L + Y_C).
        y_real = div(_ONE, r_d) if r_d > _ZERO else _ZERO
        y_imag = _ZERO
        if l_d > _ZERO:
            y_imag = y_imag - div(_ONE, mul(omega, l_d))
        if c_d > _ZERO:
            y_imag = y_imag + mul(omega, c_d)
        y_sq = mul(y_real, y_real) + mul(y_imag, y_imag)
        if y_sq == _ZERO:
            raise InvalidInputError("병렬 admittance가 0입니다.")
        z_real = div(y_real, y_sq)
        z_imag = div(-y_imag, y_sq)

    trace.step("z_real", str(z_real))
    trace.step("z_imag", str(z_imag))

    magnitude = _sqrt_mp(mul(z_real, z_real) + mul(z_imag, z_imag))
    phase_deg = _atan2_deg_mp(z_imag, z_real)
    trace.step("magnitude", str(magnitude))
    trace.step("phase_deg", str(phase_deg))
    trace.output({"magnitude": str(magnitude), "phase_deg": str(phase_deg)})

    return {
        "magnitude": str(magnitude),
        "phase_deg": str(phase_deg),
        "real":      str(z_real),
        "imag":      str(z_imag),
        "trace":     trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="engineering",
    name="rlc_time_constant",
    description=(
        "RC·RL·RLC 회로의 시정수(τ) 계산. "
        "mode: 'rc' (τ=RC), 'rl' (τ=L/R), 'rlc' (감쇠율 α=R/(2L), ω0=1/√(LC))."
    ),
    version="1.0.0",
)
def rlc_time_constant(
    mode:        str,
    resistance:  str | None = None,
    inductance:  str | None = None,
    capacitance: str | None = None,
) -> dict[str, Any]:
    """Compute RC, RL, or RLC time constant / characteristic frequencies.

    Args:
        mode:        'rc' | 'rl' | 'rlc'
        resistance:  R (Ω, > 0)
        inductance:  L (H, > 0) — required for rl/rlc
        capacitance: C (F, > 0) — required for rc/rlc

    Returns:
        - rc  : {tau, trace}
        - rl  : {tau, trace}
        - rlc : {alpha, omega0, zeta, regime, trace}
    """
    trace = CalcTrace(tool="engineering.rlc_time_constant", formula="")
    trace.input("mode", mode)

    if mode == "rc":
        if resistance is None or capacitance is None:
            raise InvalidInputError("rc 모드에는 resistance, capacitance가 필요합니다.")
        r_d = D(resistance)
        c_d = D(capacitance)
        if r_d <= _ZERO or c_d <= _ZERO:
            raise InvalidInputError("resistance, capacitance는 0 초과여야 합니다.")
        trace.formula = "τ = R × C"
        tau = mul(r_d, c_d)
        trace.step("tau", str(tau))
        trace.output({"tau": str(tau)})
        return {"tau": str(tau), "trace": trace.to_dict()}

    if mode == "rl":
        if resistance is None or inductance is None:
            raise InvalidInputError("rl 모드에는 resistance, inductance가 필요합니다.")
        r_d = D(resistance)
        l_d = D(inductance)
        if r_d <= _ZERO or l_d <= _ZERO:
            raise InvalidInputError("resistance, inductance는 0 초과여야 합니다.")
        trace.formula = "τ = L / R"
        tau = div(l_d, r_d)
        trace.step("tau", str(tau))
        trace.output({"tau": str(tau)})
        return {"tau": str(tau), "trace": trace.to_dict()}

    if mode == "rlc":
        if resistance is None or inductance is None or capacitance is None:
            raise InvalidInputError("rlc 모드에는 R, L, C 모두 필요합니다.")
        r_d = D(resistance)
        l_d = D(inductance)
        c_d = D(capacitance)
        if r_d <= _ZERO or l_d <= _ZERO or c_d <= _ZERO:
            raise InvalidInputError("R, L, C는 모두 0 초과여야 합니다.")
        trace.formula = "α = R/(2L); ω₀ = 1/√(LC); ζ = α/ω₀"
        alpha  = div(r_d, mul(_TWO, l_d))
        omega0 = div(_ONE, _sqrt_mp(mul(l_d, c_d)))
        zeta   = div(alpha, omega0)
        if zeta > _ONE:
            regime = "overdamped"
        elif zeta == _ONE:
            regime = "critically_damped"
        else:
            regime = "underdamped"
        trace.step("alpha",  str(alpha))
        trace.step("omega0", str(omega0))
        trace.step("zeta",   str(zeta))
        trace.step("regime", regime)
        trace.output({"alpha": str(alpha), "omega0": str(omega0), "zeta": str(zeta), "regime": regime})
        return {
            "alpha":  str(alpha),
            "omega0": str(omega0),
            "zeta":   str(zeta),
            "regime": regime,
            "trace":  trace.to_dict(),
        }

    raise InvalidInputError(f"mode는 'rc', 'rl', 'rlc' 중 하나여야 합니다. 입력: {mode!r}")


@REGISTRY.tool(
    namespace="engineering",
    name="lc_resonant_frequency",
    description="LC 공진 주파수 f0 = 1 / (2π√(LC)). inductance 는 인덕턴스(H), capacitance 는 정전용량(F), 결과는 Hz.",
    version="1.0.0",
)
def lc_resonant_frequency(inductance: str, capacitance: str) -> dict[str, Any]:
    """Compute LC resonant frequency f₀ = 1/(2π√(LC))."""
    trace = CalcTrace(
        tool="engineering.lc_resonant_frequency",
        formula="f = 1 / (2π√(LC))",
    )
    l_d = D(inductance)
    c_d = D(capacitance)
    if l_d <= _ZERO or c_d <= _ZERO:
        raise InvalidInputError("inductance, capacitance는 0 초과여야 합니다.")

    trace.input("inductance",  inductance)
    trace.input("capacitance", capacitance)

    sqrt_lc = _sqrt_mp(mul(l_d, c_d))
    two_pi  = mul(_TWO, _pi_dec())
    freq    = div(_ONE, mul(two_pi, sqrt_lc))

    trace.step("sqrt_lc", str(sqrt_lc))
    trace.step("frequency", str(freq))
    trace.output(str(freq))

    return {"frequency": str(freq), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="engineering",
    name="rc_filter_cutoff",
    description=(
        "RC 필터 차단 주파수 fc = 1/(2πRC). "
        "filter_type='low_pass' 또는 'high_pass' (수식 동일, 해석만 다름)."
    ),
    version="1.0.0",
)
def rc_filter_cutoff(
    resistance:  str,
    capacitance: str,
    filter_type: str = "low_pass",
) -> dict[str, Any]:
    """Compute the -3 dB cutoff frequency of a first-order RC filter."""
    trace = CalcTrace(
        tool="engineering.rc_filter_cutoff",
        formula="fc = 1 / (2π R C)",
    )
    r_d = D(resistance)
    c_d = D(capacitance)
    if r_d <= _ZERO or c_d <= _ZERO:
        raise InvalidInputError("resistance, capacitance는 0 초과여야 합니다.")
    if filter_type not in ("low_pass", "high_pass"):
        raise InvalidInputError("filter_type은 'low_pass' 또는 'high_pass'여야 합니다.")

    trace.input("resistance",  resistance)
    trace.input("capacitance", capacitance)
    trace.input("filter_type", filter_type)

    two_pi  = mul(_TWO, _pi_dec())
    cutoff  = div(_ONE, mul(two_pi, mul(r_d, c_d)))

    trace.step("cutoff", str(cutoff))
    trace.output({"cutoff_hz": str(cutoff), "filter_type": filter_type})

    return {
        "cutoff_hz":   str(cutoff),
        "filter_type": filter_type,
        "trace":       trace.to_dict(),
    }
