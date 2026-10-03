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
from typing import Literal, NotRequired, cast

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
class SafetyFactorResult(TracedResult):
    safety_factor: str
    verdict:       Literal["safe", "unsafe"]


@REGISTRY.tool(
    namespace="engineering",
    name="safety_factor",
    description=(
        "안전율 SF = 허용응력 / |작용응력| 을 계산하고 SF 1 이상이면 'safe', 미만이면 'unsafe' 를 "
        "반환한다. 두 응력은 같은 단위(Pa 또는 MPa)이며 allowable_stress 는 0 초과, applied_stress 는 "
        "0 이 아니어야 하고 부호는 무시된다. 요구 안전율(예: 1.5)과 비교하지 않으므로 safe 만으로 "
        "설계 적합을 판단하면 안 된다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def safety_factor(
    allowable_stress: str,
    applied_stress:   str,
) -> SafetyFactorResult:
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

    return cast(SafetyFactorResult, {
        "safety_factor": str(sf),
        "verdict":       verdict,
        "trace":         trace.to_dict(),
    })


# ---------------------------------------------------------------------------
# Thermal expansion strain
# ---------------------------------------------------------------------------
class ThermalExpansionStrainResult(TracedResult):
    strain:       str
    delta_length: NotRequired[str]


@REGISTRY.tool(
    namespace="engineering",
    name="thermal_expansion_strain",
    description=(
        "선팽창 변형률 ε = α·ΔT 를 계산하고 length(0 초과)를 주면 길이 변화 ΔL = ε·L₀ 도 "
        "반환한다. alpha 는 선팽창계수(1/K), delta_t 는 K 또는 °C 의 온도 변화량이며 음수면 수축이다. "
        "온도 자체(예: 20°C)가 아니라 변화량을 넣어야 한다. ΔL 은 length 와 같은 단위. 1차원 "
        "자유 팽창만 다루며 구속 열응력은 계산하지 않는다. 반올림 없음."
    ),
    version="1.0.0",
)
def thermal_expansion_strain(
    alpha:    str,
    delta_t:  str,
    length:   str | None = None,
) -> ThermalExpansionStrainResult:
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

    result = cast(ThermalExpansionStrainResult, {"strain": str(strain), "trace": trace.to_dict()})
    if delta_length is not None:
        result["delta_length"] = delta_length
    return result


# ---------------------------------------------------------------------------
# S-N fatigue life (Basquin)
# ---------------------------------------------------------------------------
class SnFatigueLifeResult(TracedResult):
    cycles: str


@REGISTRY.tool(
    namespace="engineering",
    name="sn_fatigue_life",
    description=(
        "바스퀸 식 S_a = S_f'·(2N_f)^b 를 N_f = 0.5·(S_a/S_f')^(1/b) 로 풀어 파손까지의 사이클 수를 "
        "구한다(반전 횟수 2N_f 가 아니라 사이클 N_f). stress_amplitude 와 fatigue_strength_coeff 는 "
        "같은 응력 단위로 0 초과, basquin_exponent 는 음수(통상 -0.05 ~ -0.12). 평균응력 보정과 "
        "피로한도는 반영하지 않는다. 거듭제곱은 30자리 유효숫자."
    ),
    version="1.0.0",
)
def sn_fatigue_life(
    stress_amplitude:         str,
    fatigue_strength_coeff:   str,
    basquin_exponent:         str,
) -> SnFatigueLifeResult:
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

    return cast(SnFatigueLifeResult, {"cycles": str(cycles), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Hardness conversion
# ---------------------------------------------------------------------------
# 공학적으로 신뢰되는 강재 근사식 (ASTM E140 단순화):
#   HV ≈ 0.95 × HB                              (Brinell → Vickers)
#   HRC ≈ 88.887 − 0.058 × HV                    (Vickers → Rockwell C, HV 범위 240-800)
#   (역변환은 각 식의 단순 역함수).
#
# 이 근사식은 비철금속이나 극단 영역에서는 오차가 크므로
# trace.formula에 출처를 명시한다.
_HARD_FROM = frozenset({"HV", "HB", "HRC"})


class HardnessConvertResult(TracedResult):
    value: str
    scale: Literal["HV", "HB", "HRC"]


@REGISTRY.tool(
    namespace="engineering",
    name="hardness_convert",
    description=(
        "강재의 경도를 HV, HB, HRC 사이에서 근사식(HV ≈ 0.95·HB, HRC ≈ 88.887 − 0.058·HV)으로 "
        "환산한다. value 는 0 초과이고 HRC 입력은 88.887 미만이어야 한다. 선형 근사라 적용 범위는 "
        "HV 240~800 정도이며 그 밖이나 비철금속은 오차가 크므로 정밀 환산에는 ASTM E140 표를 쓴다. "
        "반올림 없는 Decimal 문자열."
    ),
    version="1.0.0",
)
def hardness_convert(
    value:      str,
    from_scale: str,
    to_scale:   str,
) -> HardnessConvertResult:
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

    return cast(HardnessConvertResult, {
        "value":   str(out),
        "scale":   to_scale,
        "trace":   trace.to_dict(),
    })
