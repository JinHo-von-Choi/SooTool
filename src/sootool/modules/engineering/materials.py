"""Materials engineering tools (Tier 2).

Tools:
  - safety_factor            : SF = σ_allow / σ_applied
  - thermal_expansion_strain : ε = α ΔT (선팽창 변형률)
  - sn_fatigue_life          : Basquin S = S_f'·(2 N_f)^b → cycles N_f
  - hardness_convert         : HV ↔ HB ↔ HRC 근사 환산

ADR-001 Decimal, ADR-003 trace, ADR-007 stateless.
비정수 멱은 mpmath workdps(50) → mpmath_to_decimal(digits=30).
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


def _pow_mp(base: Decimal, exponent: Decimal) -> Decimal:
    if base <= _ZERO:
        raise InvalidInputError("거듭제곱의 밑은 0 초과여야 합니다.")
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(
            mpmath.power(mpmath.mpf(str(base)), mpmath.mpf(str(exponent))),
            digits=_OUT_DIG,
        )


# ---------------------------------------------------------------------------
# Safety factor
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="safety_factor",
    description=(
        "안전율 SF = σ_allow / σ_applied. σ_applied는 절댓값으로 처리. "
        "verdict: 'safe' (SF ≥ 1), 'unsafe' (SF < 1)."
    ),
    version="1.0.0",
)
def safety_factor(
    allowable_stress: str,
    applied_stress:   str,
) -> dict[str, Any]:
    """Compute safety factor SF and categorical verdict."""
    trace = CalcTrace(tool="engineering.safety_factor", formula="SF = σ_allow / |σ_applied|")
    sig_allow = D(allowable_stress)
    sig_app = D(applied_stress)
    if sig_allow <= _ZERO:
        raise InvalidInputError("allowable_stress는 0 초과여야 합니다.")
    if sig_app == _ZERO:
        raise InvalidInputError("applied_stress는 0이 될 수 없습니다.")

    trace.input("allowable_stress", allowable_stress)
    trace.input("applied_stress",   applied_stress)

    sig_app_abs = abs(sig_app)
    sf = div(sig_allow, sig_app_abs)
    verdict = "safe" if sf >= _ONE else "unsafe"

    trace.step("applied_abs",   str(sig_app_abs))
    trace.step("safety_factor", str(sf))
    trace.step("verdict",       verdict)
    trace.output({"safety_factor": str(sf), "verdict": verdict})

    return {
        "safety_factor": str(sf),
        "verdict":       verdict,
        "trace":         trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Thermal expansion strain
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="thermal_expansion_strain",
    description=(
        "열팽창 변형률 ε = α·ΔT (선형 1차원). "
        "alpha는 선팽창계수 (1/K), delta_t는 온도 변화 (K 또는 °C 차). "
        "delta_length = alpha·ΔT·L₀ (length 제공 시)."
    ),
    version="1.0.0",
)
def thermal_expansion_strain(
    alpha:    str,
    delta_t:  str,
    length:   str | None = None,
) -> dict[str, Any]:
    """Compute thermal strain ε and optionally the absolute length change."""
    trace = CalcTrace(
        tool="engineering.thermal_expansion_strain",
        formula="ε = α·ΔT; ΔL = ε·L₀",
    )
    a_d = D(alpha)
    dt_d = D(delta_t)

    trace.input("alpha",   alpha)
    trace.input("delta_t", delta_t)

    strain = mul(a_d, dt_d)
    trace.step("strain", str(strain))

    delta_length: str | None = None
    if length is not None:
        l_d = D(length)
        if l_d <= _ZERO:
            raise InvalidInputError("length는 0 초과여야 합니다.")
        trace.input("length", length)
        dl = mul(strain, l_d)
        delta_length = str(dl)
        trace.step("delta_length", delta_length)

    if delta_length is not None:
        trace.output({"strain": str(strain), "delta_length": delta_length})
    else:
        trace.output({"strain": str(strain)})

    result: dict[str, Any] = {"strain": str(strain), "trace": trace.to_dict()}
    if delta_length is not None:
        result["delta_length"] = delta_length
    return result


# ---------------------------------------------------------------------------
# S-N fatigue life (Basquin)
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="sn_fatigue_life",
    description=(
        "Basquin 피로수명: S_a = S_f'·(2 N_f)^b → "
        "N_f = 0.5·(S_a / S_f')^(1/b). "
        "S_f' (fatigue_strength_coeff) > 0, Basquin 지수 b < 0 (일반적으로 −0.05 ~ −0.12)."
    ),
    version="1.0.0",
)
def sn_fatigue_life(
    stress_amplitude:         str,
    fatigue_strength_coeff:   str,
    basquin_exponent:         str,
) -> dict[str, Any]:
    """Compute cycles to failure N_f using the Basquin relation."""
    trace = CalcTrace(
        tool="engineering.sn_fatigue_life",
        formula="N_f = 0.5·(S_a / S_f')^(1/b)",
    )
    sa_d = D(stress_amplitude)
    sf_d = D(fatigue_strength_coeff)
    b_d = D(basquin_exponent)

    if sa_d <= _ZERO:
        raise InvalidInputError("stress_amplitude는 0 초과여야 합니다.")
    if sf_d <= _ZERO:
        raise InvalidInputError("fatigue_strength_coeff는 0 초과여야 합니다.")
    if b_d >= _ZERO:
        raise InvalidInputError("basquin_exponent b는 음수여야 합니다.")

    trace.input("stress_amplitude",       stress_amplitude)
    trace.input("fatigue_strength_coeff", fatigue_strength_coeff)
    trace.input("basquin_exponent",       basquin_exponent)

    ratio = div(sa_d, sf_d)
    inv_b = div(_ONE, b_d)
    ratio_pow = _pow_mp(ratio, inv_b)
    cycles = mul(Decimal("0.5"), ratio_pow)

    trace.step("ratio",       str(ratio))
    trace.step("inv_b",       str(inv_b))
    trace.step("ratio_power", str(ratio_pow))
    trace.step("cycles",      str(cycles))
    trace.output(str(cycles))

    return {"cycles": str(cycles), "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Hardness conversion
# ---------------------------------------------------------------------------
# 공학적으로 신뢰되는 강재 근사식 (ASTM E140 단순화):
#   HV ≈ 0.95 × HB                              (Brinell → Vickers)
#   HRC ≈ 88.887 − 0.058 × HV                    (Vickers → Rockwell C, HV 범위 240–800)
#   (역변환은 각 식의 단순 역함수).
#
# 이 근사식은 비철금속이나 극단 영역에서는 오차가 크므로
# trace.formula에 출처를 명시한다.
_HARD_FROM = frozenset({"HV", "HB", "HRC"})


@REGISTRY.tool(
    namespace="engineering",
    name="hardness_convert",
    description=(
        "경도 환산 (강재 ASTM E140 단순식). "
        "HV ≈ 0.95·HB,  HRC ≈ 88.887 − 0.058·HV. "
        "from_scale·to_scale ∈ {HV, HB, HRC}."
    ),
    version="1.0.0",
)
def hardness_convert(
    value:      str,
    from_scale: str,
    to_scale:   str,
) -> dict[str, Any]:
    """Convert between HV, HB, HRC hardness scales (steels, approximate)."""
    trace = CalcTrace(
        tool="engineering.hardness_convert",
        formula="HV ≈ 0.95·HB;  HRC ≈ 88.887 − 0.058·HV",
    )
    if from_scale not in _HARD_FROM or to_scale not in _HARD_FROM:
        raise InvalidInputError(f"scale은 {sorted(_HARD_FROM)} 중 하나여야 합니다.")
    v_d = D(value)
    if v_d <= _ZERO:
        raise InvalidInputError("value는 0 초과여야 합니다.")

    trace.input("value",      value)
    trace.input("from_scale", from_scale)
    trace.input("to_scale",   to_scale)

    # Normalize to HV internally, then emit target.
    c1 = Decimal("0.95")        # HV / HB
    a  = Decimal("88.887")
    bc = Decimal("0.058")       # HRC = a − bc·HV

    if from_scale == "HV":
        hv = v_d
    elif from_scale == "HB":
        hv = mul(c1, v_d)
    else:  # HRC
        # hrc = a − bc·hv  →  hv = (a − hrc) / bc
        if v_d >= a:
            raise InvalidInputError("HRC 값은 88.887 미만이어야 합니다.")
        hv = div(a - v_d, bc)
    trace.step("normalized_HV", str(hv))

    if to_scale == "HV":
        out = hv
    elif to_scale == "HB":
        out = div(hv, c1)
    else:  # HRC
        out = a - mul(bc, hv)

    trace.step(f"converted_{to_scale}", str(out))
    trace.output(str(out))

    return {
        "value":   str(out),
        "scale":   to_scale,
        "trace":   trace.to_dict(),
    }
