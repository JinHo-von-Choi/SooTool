"""AC electrical engineering tools.

Tools:
  - ac_impedance           : R/L/C series or parallel AC impedance (magnitude + phase)
  - rlc_time_constant      : RC, RL, or RLC circuit time constant
  - lc_resonant_frequency  : LC resonant frequency f = 1/(2π√(LC))
  - rc_filter_cutoff       : RC low-pass / high-pass cutoff frequency
  - capacitor_combine      : series/parallel capacitance combination
  - inductor_combine       : series/parallel inductance combination
  - three_phase_power      : balanced 3-phase real/apparent/reactive power (wye/delta)
  - power_factor_correction: shunt capacitance for PF correction
  - db_convert             : voltage ratio / power ratio / Np / dBm conversions
  - resistor_color_code    : 4-band or 5-band resistor color code decode
  - opamp_gain             : inverting / non-inverting op-amp gain

내부 자료형: Decimal 입출력, 제곱근·아크탄젠트·로그는 mpmath 고정밀 경로.
ADR-001 Decimal 의무, ADR-003 감사 로그, ADR-007 stateless, ADR-008 자료형 이원화 준수.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, add, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO     = Decimal("0")
_ONE      = Decimal("1")
_TWO      = Decimal("2")
_MP_DPS   = 50
_OUT_DIG  = 30


def _sqrt_mp(x: Decimal) -> Decimal:
    """High-precision square root via mpmath, returned as Decimal."""
    if x < _ZERO:
        raise InvalidInputError("제곱근의 피연산자는 0 이상이어야 합니다.")
    if x == _ZERO:
        return _ZERO
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.sqrt(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _atan2_deg_mp(y: Decimal, x: Decimal) -> Decimal:
    """Four-quadrant atan2 in degrees via mpmath."""
    with mpmath.workdps(_MP_DPS):
        rad = mpmath.atan2(mpmath.mpf(str(y)), mpmath.mpf(str(x)))
        deg = rad * mpmath.mpf("180") / mpmath.pi
        return mpmath_to_decimal(deg, digits=_OUT_DIG)


def _pi_dec() -> Decimal:
    """High-precision π as Decimal."""
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.pi, digits=_OUT_DIG)


# ---------------------------------------------------------------------------
# AC impedance (R/L/C series or parallel)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# RC / RL / RLC time constant
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# LC resonant frequency
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="lc_resonant_frequency",
    description="LC 공진 주파수 f = 1 / (2π√(LC)).",
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


# ---------------------------------------------------------------------------
# RC filter cutoff frequency
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Capacitor and inductor combination
# ---------------------------------------------------------------------------


def _combine_network(
    values: list[str],
    topology: str,
    series_rule: str,   # "sum" or "reciprocal"
    parallel_rule: str,
    label: str,
) -> Decimal:
    if not values:
        raise InvalidInputError(f"{label} 리스트는 최소 1개 이상이어야 합니다.")
    decs = [D(v) for v in values]
    for i, v in enumerate(decs):
        if v <= _ZERO:
            raise InvalidInputError(f"{label}[{i}]는 0 초과여야 합니다. 입력값: {values[i]!r}")
    if topology not in ("series", "parallel"):
        raise InvalidInputError("topology는 'series' 또는 'parallel'이어야 합니다.")

    rule = series_rule if topology == "series" else parallel_rule
    if rule == "sum":
        return add(*decs)
    # reciprocal
    reciprocal_sum = add(*[div(_ONE, v) for v in decs])
    return div(_ONE, reciprocal_sum)


@REGISTRY.tool(
    namespace="engineering",
    name="capacitor_combine",
    description=(
        "커패시터 직렬/병렬 합성. "
        "series: 1/C = Σ(1/Cᵢ), parallel: C = ΣCᵢ."
    ),
    version="1.0.0",
)
def capacitor_combine(capacitors: list[str], topology: str) -> dict[str, Any]:
    """Compute equivalent capacitance."""
    trace = CalcTrace(
        tool="engineering.capacitor_combine",
        formula="series: 1/C = Σ(1/Cᵢ); parallel: C = ΣCᵢ",
    )
    trace.input("capacitors", capacitors)
    trace.input("topology",   topology)

    total = _combine_network(
        capacitors,
        topology,
        series_rule="reciprocal",
        parallel_rule="sum",
        label="capacitors",
    )
    trace.step("total", str(total))
    trace.output(str(total))

    return {"total": str(total), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="engineering",
    name="inductor_combine",
    description=(
        "인덕터 직렬/병렬 합성. "
        "series: L = ΣLᵢ, parallel: 1/L = Σ(1/Lᵢ)."
    ),
    version="1.0.0",
)
def inductor_combine(inductors: list[str], topology: str) -> dict[str, Any]:
    """Compute equivalent inductance."""
    trace = CalcTrace(
        tool="engineering.inductor_combine",
        formula="series: L = ΣLᵢ; parallel: 1/L = Σ(1/Lᵢ)",
    )
    trace.input("inductors", inductors)
    trace.input("topology",  topology)

    total = _combine_network(
        inductors,
        topology,
        series_rule="sum",
        parallel_rule="reciprocal",
        label="inductors",
    )
    trace.step("total", str(total))
    trace.output(str(total))

    return {"total": str(total), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Three-phase power
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="three_phase_power",
    description=(
        "균형 3상 전력: P = √3 · V_LL · I_L · cos(φ). "
        "connection: 'wye' 또는 'delta' (선간·선전류 수식 동일)."
    ),
    version="1.0.0",
)
def three_phase_power(
    line_voltage: str,
    line_current: str,
    power_factor: str,
    connection:   str = "wye",
) -> dict[str, Any]:
    """Compute balanced three-phase real, reactive, and apparent power.

    Formulas (line quantities):
      S = √3 · V_LL · I_L        (apparent, VA)
      P = S · cos(φ)             (real, W)
      Q = S · sin(φ) = √(S² − P²) (reactive, VAR)
    """
    trace = CalcTrace(
        tool="engineering.three_phase_power",
        formula="S = √3 V_LL I_L; P = S cosφ; Q = √(S² − P²)",
    )
    if connection not in ("wye", "delta"):
        raise InvalidInputError("connection은 'wye' 또는 'delta'여야 합니다.")

    v_d  = D(line_voltage)
    i_d  = D(line_current)
    pf_d = D(power_factor)
    if v_d <= _ZERO or i_d <= _ZERO:
        raise InvalidInputError("line_voltage, line_current는 0 초과여야 합니다.")
    if pf_d < Decimal("-1") or pf_d > _ONE:
        raise InvalidInputError("power_factor는 [-1, 1] 범위여야 합니다.")

    trace.input("line_voltage", line_voltage)
    trace.input("line_current", line_current)
    trace.input("power_factor", power_factor)
    trace.input("connection",   connection)

    sqrt3 = _sqrt_mp(Decimal("3"))
    apparent = mul(sqrt3, mul(v_d, i_d))
    real     = mul(apparent, pf_d)
    reactive_sq = mul(apparent, apparent) - mul(real, real)
    if reactive_sq < _ZERO:
        reactive_sq = _ZERO
    reactive = _sqrt_mp(reactive_sq)

    trace.step("apparent", str(apparent))
    trace.step("real",     str(real))
    trace.step("reactive", str(reactive))
    trace.output({"apparent": str(apparent), "real": str(real), "reactive": str(reactive)})

    return {
        "apparent": str(apparent),
        "real":     str(real),
        "reactive": str(reactive),
        "trace":    trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Power factor correction capacitance
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="power_factor_correction",
    description=(
        "역률 보정용 병렬 커패시턴스 C = Q_c / (2π f V²), "
        "Q_c = P · (tan φ₁ − tan φ₂)."
    ),
    version="1.0.0",
)
def power_factor_correction(
    real_power:          str,
    current_pf:          str,
    target_pf:           str,
    voltage:             str,
    frequency:           str,
) -> dict[str, Any]:
    """Compute the shunt capacitance required to correct the power factor.

    Assumes lagging load (inductive).
    """
    trace = CalcTrace(
        tool="engineering.power_factor_correction",
        formula="C = P(tan φ₁ − tan φ₂) / (2π f V²)",
    )

    p_d   = D(real_power)
    pf1_d = D(current_pf)
    pf2_d = D(target_pf)
    v_d   = D(voltage)
    f_d   = D(frequency)

    if p_d <= _ZERO:
        raise InvalidInputError("real_power는 0 초과여야 합니다.")
    if v_d <= _ZERO or f_d <= _ZERO:
        raise InvalidInputError("voltage, frequency는 0 초과여야 합니다.")
    for name, val in [("current_pf", pf1_d), ("target_pf", pf2_d)]:
        if val <= _ZERO or val > _ONE:
            raise InvalidInputError(f"{name}는 (0, 1] 범위여야 합니다.")
    if pf2_d <= pf1_d:
        raise InvalidInputError("target_pf는 current_pf보다 커야 합니다.")

    trace.input("real_power", real_power)
    trace.input("current_pf", current_pf)
    trace.input("target_pf",  target_pf)
    trace.input("voltage",    voltage)
    trace.input("frequency",  frequency)

    # tan φ from cos φ: tan = sqrt(1 - cos²) / cos
    tan1 = div(_sqrt_mp(_ONE - mul(pf1_d, pf1_d)), pf1_d)
    tan2 = div(_sqrt_mp(_ONE - mul(pf2_d, pf2_d)), pf2_d)
    qc   = mul(p_d, tan1 - tan2)

    two_pi = mul(_TWO, _pi_dec())
    denom  = mul(two_pi, mul(f_d, mul(v_d, v_d)))
    c      = div(qc, denom)

    trace.step("tan_phi_1", str(tan1))
    trace.step("tan_phi_2", str(tan2))
    trace.step("reactive_to_cancel", str(qc))
    trace.step("capacitance", str(c))
    trace.output({"capacitance": str(c), "reactive_power_canceled": str(qc)})

    return {
        "capacitance":              str(c),
        "reactive_power_canceled":  str(qc),
        "trace":                    trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# dB conversion
# ---------------------------------------------------------------------------


_DB_MODES = frozenset(
    {"v_to_db", "p_to_db", "db_to_v", "db_to_p", "np_to_db", "db_to_np",
     "w_to_dbm", "dbm_to_w"}
)


@REGISTRY.tool(
    namespace="engineering",
    name="db_convert",
    description=(
        "dB·Np·dBm 상호 변환. modes: v_to_db (20log10 비), p_to_db (10log10), "
        "db_to_v, db_to_p, np_to_db, db_to_np, w_to_dbm, dbm_to_w."
    ),
    version="1.0.0",
)
def db_convert(mode: str, value: str, reference: str = "1") -> dict[str, Any]:
    """Convert between linear quantities and decibel/neper scales.

    Args:
        mode:      변환 모드 (위 설명 참조)
        value:     입력 값 (Decimal string)
        reference: 기준값 (Decimal string). v_to_db/p_to_db에서 비율 분모로 사용.

    Returns:
        {result, trace}
    """
    trace = CalcTrace(tool="engineering.db_convert", formula="")
    if mode not in _DB_MODES:
        raise InvalidInputError(f"mode는 {sorted(_DB_MODES)} 중 하나여야 합니다. 입력: {mode!r}")

    trace.input("mode", mode)
    trace.input("value", value)
    trace.input("reference", reference)

    v_d   = D(value)
    ref_d = D(reference)

    with mpmath.workdps(_MP_DPS):
        v_mp   = mpmath.mpf(str(v_d))
        ref_mp = mpmath.mpf(str(ref_d))
        ten    = mpmath.mpf("10")
        twenty = mpmath.mpf("20")

        if mode == "v_to_db":
            if v_mp <= 0 or ref_mp <= 0:
                raise InvalidInputError("v_to_db는 양수 비율이 필요합니다.")
            trace.formula = "dB = 20 log10(V/V_ref)"
            result = twenty * mpmath.log10(v_mp / ref_mp)

        elif mode == "p_to_db":
            if v_mp <= 0 or ref_mp <= 0:
                raise InvalidInputError("p_to_db는 양수 비율이 필요합니다.")
            trace.formula = "dB = 10 log10(P/P_ref)"
            result = ten * mpmath.log10(v_mp / ref_mp)

        elif mode == "db_to_v":
            trace.formula = "V/V_ref = 10^(dB/20)"
            result = mpmath.power(ten, v_mp / twenty)

        elif mode == "db_to_p":
            trace.formula = "P/P_ref = 10^(dB/10)"
            result = mpmath.power(ten, v_mp / ten)

        elif mode == "np_to_db":
            trace.formula = "dB = Np × (20 / ln(10))"
            result = v_mp * (twenty / mpmath.log(ten))

        elif mode == "db_to_np":
            trace.formula = "Np = dB × (ln(10) / 20)"
            result = v_mp * (mpmath.log(ten) / twenty)

        elif mode == "w_to_dbm":
            if v_mp <= 0:
                raise InvalidInputError("w_to_dbm은 양수 전력이 필요합니다.")
            trace.formula = "dBm = 10 log10(P_W / 1 mW)"
            result = ten * mpmath.log10(v_mp / mpmath.mpf("0.001"))

        else:  # dbm_to_w
            trace.formula = "P_W = 10^(dBm/10) × 1 mW"
            result = mpmath.power(ten, v_mp / ten) * mpmath.mpf("0.001")

        result_dec = mpmath_to_decimal(result, digits=_OUT_DIG)

    trace.step("result", str(result_dec))
    trace.output(str(result_dec))

    return {"result": str(result_dec), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Resistor color code (4-band / 5-band)
# ---------------------------------------------------------------------------


_COLOR_DIGITS: dict[str, int] = {
    "black":   0,
    "brown":   1,
    "red":     2,
    "orange":  3,
    "yellow":  4,
    "green":   5,
    "blue":    6,
    "violet":  7,
    "gray":    8,
    "white":   9,
}

_COLOR_MULTIPLIER: dict[str, Decimal] = {
    "black":   Decimal("1"),
    "brown":   Decimal("10"),
    "red":     Decimal("100"),
    "orange":  Decimal("1000"),
    "yellow":  Decimal("10000"),
    "green":   Decimal("100000"),
    "blue":    Decimal("1000000"),
    "violet":  Decimal("10000000"),
    "gray":    Decimal("100000000"),
    "white":   Decimal("1000000000"),
    "gold":    Decimal("0.1"),
    "silver":  Decimal("0.01"),
}

_COLOR_TOLERANCE: dict[str, Decimal] = {
    "brown":   Decimal("1"),
    "red":     Decimal("2"),
    "green":   Decimal("0.5"),
    "blue":    Decimal("0.25"),
    "violet":  Decimal("0.1"),
    "gray":    Decimal("0.05"),
    "gold":    Decimal("5"),
    "silver":  Decimal("10"),
}


@REGISTRY.tool(
    namespace="engineering",
    name="resistor_color_code",
    description=(
        "저항기 4밴드 또는 5밴드 컬러코드 해독. "
        "4밴드: [digit1, digit2, multiplier, tolerance], "
        "5밴드: [digit1, digit2, digit3, multiplier, tolerance]."
    ),
    version="1.0.0",
)
def resistor_color_code(bands: list[str]) -> dict[str, Any]:
    """Decode a 4-band or 5-band resistor color code."""
    trace = CalcTrace(
        tool="engineering.resistor_color_code",
        formula="R = (digits × 10^multiplier_index) ± tolerance%",
    )
    trace.input("bands", bands)

    if len(bands) not in (4, 5):
        raise InvalidInputError("bands는 4개 또는 5개여야 합니다.")
    bands_lower = [b.lower().strip() for b in bands]

    digit_count = 2 if len(bands_lower) == 4 else 3
    digit_bands = bands_lower[:digit_count]
    multiplier_band = bands_lower[digit_count]
    tolerance_band  = bands_lower[digit_count + 1]

    digits = 0
    for i, band in enumerate(digit_bands):
        if band not in _COLOR_DIGITS:
            raise InvalidInputError(f"자릿수 밴드 {i} 색상이 유효하지 않습니다: {band!r}")
        digits = digits * 10 + _COLOR_DIGITS[band]

    if multiplier_band not in _COLOR_MULTIPLIER:
        raise InvalidInputError(f"승수 밴드 색상이 유효하지 않습니다: {multiplier_band!r}")
    if tolerance_band not in _COLOR_TOLERANCE:
        raise InvalidInputError(
            f"허용오차 밴드 색상이 유효하지 않습니다: {tolerance_band!r}"
        )

    multiplier = _COLOR_MULTIPLIER[multiplier_band]
    tolerance  = _COLOR_TOLERANCE[tolerance_band]
    resistance = mul(Decimal(digits), multiplier)

    trace.step("digits",     str(digits))
    trace.step("multiplier", str(multiplier))
    trace.step("tolerance",  str(tolerance))
    trace.step("resistance", str(resistance))
    trace.output({
        "resistance_ohm": str(resistance),
        "tolerance_pct":  str(tolerance),
    })

    return {
        "resistance_ohm": str(resistance),
        "tolerance_pct":  str(tolerance),
        "trace":          trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Op-amp basic gain
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="opamp_gain",
    description=(
        "Op-amp 기본 이득. configuration='inverting' (-Rf/Rin) "
        "또는 'non_inverting' (1 + Rf/Rin)."
    ),
    version="1.0.0",
)
def opamp_gain(
    feedback_resistance: str,
    input_resistance:    str,
    configuration:       str = "inverting",
) -> dict[str, Any]:
    """Compute ideal op-amp closed-loop voltage gain."""
    trace = CalcTrace(tool="engineering.opamp_gain", formula="")
    if configuration not in ("inverting", "non_inverting"):
        raise InvalidInputError(
            "configuration은 'inverting' 또는 'non_inverting'이어야 합니다."
        )
    rf_d = D(feedback_resistance)
    rin_d = D(input_resistance)
    if rf_d <= _ZERO or rin_d <= _ZERO:
        raise InvalidInputError("두 저항 모두 0 초과여야 합니다.")

    trace.input("feedback_resistance", feedback_resistance)
    trace.input("input_resistance",    input_resistance)
    trace.input("configuration",       configuration)

    if configuration == "inverting":
        trace.formula = "A = -Rf / Rin"
        gain = -div(rf_d, rin_d)
    else:
        trace.formula = "A = 1 + Rf / Rin"
        gain = _ONE + div(rf_d, rin_d)

    trace.step("gain", str(gain))
    trace.output(str(gain))

    return {"gain": str(gain), "trace": trace.to_dict()}
