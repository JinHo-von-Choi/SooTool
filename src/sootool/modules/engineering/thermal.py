"""Thermal engineering tools.

Tools:
  - fourier_heat_conduction : Q = -kA(dT/dx) (magnitude returned with sign convention)
  - thermal_resistance      : series/parallel thermal resistance combination
  - stefan_boltzmann        : Radiative heat transfer Q = εσA(T_s⁴ − T_surr⁴)
  - lmtd                    : Log-mean temperature difference for heat exchangers
  - convective_heat_transfer: Q = hA(T_s − T_∞)

ADR-001 Decimal 의무, ADR-003 감사 로그, ADR-007 stateless.
로그·거듭제곱은 mpmath 고정밀 경로(ADR-008).
"""
from __future__ import annotations

from decimal import Decimal
from typing import cast

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, add, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_MP_DPS  = 50
_OUT_DIG = 30

# Stefan-Boltzmann constant σ = 5.670374419e-8 W/(m²·K⁴) (2019 CODATA).
_STEFAN_BOLTZMANN = Decimal("5.670374419E-8")


def _ln_mp(x: Decimal) -> Decimal:
    """Natural logarithm via mpmath."""
    if x <= _ZERO:
        raise InvalidInputError("로그의 인수는 0 초과여야 합니다.")
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.log(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _pow4(x: Decimal) -> Decimal:
    return mul(mul(x, x), mul(x, x))


class HeatRateResult(TracedResult):
    heat_rate_w: str


# ---------------------------------------------------------------------------
# Fourier conduction
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="fourier_heat_conduction",
    description=(
        "1차원 정상상태 평판 열전도 Q = k·A·(T_hot − T_cold)/L (W)를 계산한다. "
        "thermal_conductivity W/(m·K), area m², thickness m, 온도는 K 또는 °C(차이만 사용). "
        "temperature_hot 이 temperature_cold 보다 낮으면 오류이며 역방향은 인자를 바꿔 호출한다. "
        "다층벽은 층별 L/(kA)를 구해 thermal_resistance 로 합성한다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def fourier_heat_conduction(
    thermal_conductivity: str,
    area:                 str,
    temperature_hot:      str,
    temperature_cold:     str,
    thickness:            str,
) -> HeatRateResult:
    """Compute 1-D steady conductive heat rate through a slab.

    Q = k · A · ΔT / L  (W)
    ΔT = T_hot − T_cold must be ≥ 0.
    """
    trace = CalcTrace(
        tool="engineering.fourier_heat_conduction",
        formula="Q = k A (T_hot − T_cold) / L",
    )
    k_d  = D(thermal_conductivity)
    a_d  = D(area)
    th_d = D(temperature_hot)
    tc_d = D(temperature_cold)
    l_d  = D(thickness)

    if k_d <= _ZERO:
        raise InvalidInputError("thermal_conductivity는 0 초과여야 합니다.")
    if a_d <= _ZERO:
        raise InvalidInputError("area는 0 초과여야 합니다.")
    if l_d <= _ZERO:
        raise InvalidInputError("thickness는 0 초과여야 합니다.")
    if th_d < tc_d:
        raise InvalidInputError("temperature_hot는 temperature_cold 이상이어야 합니다.")

    trace.input("thermal_conductivity", thermal_conductivity)
    trace.input("area",                 area)
    trace.input("temperature_hot",      temperature_hot)
    trace.input("temperature_cold",     temperature_cold)
    trace.input("thickness",            thickness)

    delta_t = th_d - tc_d
    heat_rate = div(mul(k_d, mul(a_d, delta_t)), l_d)

    trace.step("delta_t",   str(delta_t))
    trace.step("heat_rate", str(heat_rate))
    trace.output(str(heat_rate))

    return cast(HeatRateResult, {"heat_rate_w": str(heat_rate), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Thermal resistance combination
# ---------------------------------------------------------------------------


class ThermalResistanceResult(TracedResult):
    total: str


@REGISTRY.tool(
    namespace="engineering",
    name="thermal_resistance",
    description=(
        "열저항 K/W 를 합성한다. topology 'series' 는 R_total = ΣRᵢ, 'parallel' 은 "
        "1/R_total = Σ(1/Rᵢ). resistances 는 열저항의 숫자 문자열 목록(1개 이상, 모두 0 초과, "
        "같은 단위)이다. 0 저항(완전 전도)은 입력할 수 없고 직렬과 병렬이 섞인 회로는 단계별로 "
        "나눠 호출해야 한다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def thermal_resistance(resistances: list[str], topology: str) -> ThermalResistanceResult:
    """Compute equivalent thermal resistance (K/W)."""
    trace = CalcTrace(
        tool="engineering.thermal_resistance",
        formula="series: R = ΣRᵢ; parallel: 1/R = Σ(1/Rᵢ)",
    )
    if not resistances:
        raise InvalidInputError("resistances 리스트는 최소 1개 이상이어야 합니다.")
    if topology not in ("series", "parallel"):
        raise InvalidInputError("topology는 'series' 또는 'parallel'이어야 합니다.")

    values = [D(r) for r in resistances]
    for i, v in enumerate(values):
        if v <= _ZERO:
            raise InvalidInputError(f"resistances[{i}]는 0 초과여야 합니다.")

    trace.input("resistances", resistances)
    trace.input("topology",    topology)

    if topology == "series":
        total = add(*values)
    else:
        reciprocal_sum = add(*[div(_ONE, v) for v in values])
        total = div(_ONE, reciprocal_sum)

    trace.step("total", str(total))
    trace.output(str(total))

    return cast(ThermalResistanceResult, {"total": str(total), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Stefan-Boltzmann radiation
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="stefan_boltzmann",
    description=(
        "회색체 표면과 주위 사이의 순복사 열전달 Q = ε·σ·A·(T_s⁴ − T_surr⁴) (W)를 계산한다. "
        "σ = 5.670374419e-8 W/(m²·K⁴), emissivity 는 [0, 1], area m². 온도는 절대온도 K(0 초과)이므로 "
        "섭씨를 그대로 넣으면 틀린다. 작은 표면이 큰 주위에 둘러싸인 경우의 식이며 표면이 더 "
        "차가우면 음수. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def stefan_boltzmann(
    emissivity:          str,
    area:                str,
    temperature_surface: str,
    temperature_surround: str,
) -> HeatRateResult:
    """Compute net radiative heat transfer rate between a gray surface and surroundings."""
    trace = CalcTrace(
        tool="engineering.stefan_boltzmann",
        formula="Q = ε σ A (T_s⁴ − T_surr⁴)",
    )
    eps_d  = D(emissivity)
    a_d    = D(area)
    ts_d   = D(temperature_surface)
    tsu_d  = D(temperature_surround)

    if eps_d < _ZERO or eps_d > _ONE:
        raise InvalidInputError("emissivity는 [0, 1] 범위여야 합니다.")
    if a_d <= _ZERO:
        raise InvalidInputError("area는 0 초과여야 합니다.")
    if ts_d <= _ZERO or tsu_d <= _ZERO:
        raise InvalidInputError("절대온도는 0K 초과여야 합니다.")

    trace.input("emissivity",           emissivity)
    trace.input("area",                 area)
    trace.input("temperature_surface",  temperature_surface)
    trace.input("temperature_surround", temperature_surround)

    delta_t4 = _pow4(ts_d) - _pow4(tsu_d)
    heat_rate = mul(eps_d, mul(_STEFAN_BOLTZMANN, mul(a_d, delta_t4)))

    trace.step("delta_t4",  str(delta_t4))
    trace.step("heat_rate", str(heat_rate))
    trace.output(str(heat_rate))

    return cast(HeatRateResult, {"heat_rate_w": str(heat_rate), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# LMTD (Log-mean temperature difference)
# ---------------------------------------------------------------------------


class LmtdResult(TracedResult):
    lmtd: str


@REGISTRY.tool(
    namespace="engineering",
    name="lmtd",
    description=(
        "열교환기 대수평균온도차 LMTD = (ΔT₁ − ΔT₂)/ln(ΔT₁/ΔT₂)를 계산한다. 양 끝단의 온도차 "
        "두 값(K 또는 °C 차, 모두 0 초과)을 받고 같으면 극한값 ΔT₁ 을 반환한다. 병류와 향류에 맞게 "
        "각 끝단의 온도차를 직접 정해 넣어야 하며 다관식 열교환기의 보정계수 F 는 포함하지 않는다. "
        "ln 은 30자리 유효숫자."
    ),
    version="1.0.0",
)
def lmtd(
    delta_t_hot_inlet:  str,
    delta_t_cold_outlet: str,
) -> LmtdResult:
    """Compute log-mean temperature difference.

    Args:
        delta_t_hot_inlet:   hot-side 입구 – cold-side 대응 단(ΔT₁)
        delta_t_cold_outlet: hot-side 출구 – cold-side 대응 단(ΔT₂)

    Both ΔT values must be > 0 (positive temperature difference at each end).
    """
    trace = CalcTrace(
        tool="engineering.lmtd",
        formula="LMTD = (ΔT₁ − ΔT₂) / ln(ΔT₁ / ΔT₂)",
    )
    dt1_d = D(delta_t_hot_inlet)
    dt2_d = D(delta_t_cold_outlet)

    if dt1_d <= _ZERO or dt2_d <= _ZERO:
        raise InvalidInputError("두 온도차 모두 0 초과여야 합니다.")

    trace.input("delta_t_hot_inlet",   delta_t_hot_inlet)
    trace.input("delta_t_cold_outlet", delta_t_cold_outlet)

    if dt1_d == dt2_d:
        result = dt1_d
        trace.step("analytic_limit", "ΔT₁ == ΔT₂")
    else:
        ratio = div(dt1_d, dt2_d)
        ln_ratio = _ln_mp(ratio)
        result = div(dt1_d - dt2_d, ln_ratio)
        trace.step("ratio",    str(ratio))
        trace.step("ln_ratio", str(ln_ratio))

    trace.step("lmtd", str(result))
    trace.output(str(result))

    return cast(LmtdResult, {"lmtd": str(result), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Newton convective heat transfer
# ---------------------------------------------------------------------------


@REGISTRY.tool(
    namespace="engineering",
    name="convective_heat_transfer",
    description=(
        "뉴턴 냉각 법칙에 따른 대류 열전달 Q = h·A·(T_s − T_∞) (W)를 계산한다. "
        "heat_transfer_coefficient W/(m²·K), area m², 온도는 K 또는 °C(차이만 사용). 표면이 유체보다 "
        "뜨거우면 양수, 차가우면 음수이다. h 는 입력값이며 유동 조건에서 구해 주지 않는다. "
        "반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def convective_heat_transfer(
    heat_transfer_coefficient: str,
    area:                      str,
    temperature_surface:       str,
    temperature_fluid:         str,
) -> HeatRateResult:
    """Compute convective heat rate Q = h·A·ΔT (Newton's law of cooling)."""
    trace = CalcTrace(
        tool="engineering.convective_heat_transfer",
        formula="Q = h A (T_s − T_∞)",
    )
    h_d = D(heat_transfer_coefficient)
    a_d = D(area)
    ts_d = D(temperature_surface)
    tf_d = D(temperature_fluid)

    if h_d <= _ZERO:
        raise InvalidInputError("heat_transfer_coefficient는 0 초과여야 합니다.")
    if a_d <= _ZERO:
        raise InvalidInputError("area는 0 초과여야 합니다.")

    trace.input("heat_transfer_coefficient", heat_transfer_coefficient)
    trace.input("area",                      area)
    trace.input("temperature_surface",       temperature_surface)
    trace.input("temperature_fluid",         temperature_fluid)

    delta_t = ts_d - tf_d
    heat_rate = mul(h_d, mul(a_d, delta_t))

    trace.step("delta_t",   str(delta_t))
    trace.step("heat_rate", str(heat_rate))
    trace.output(str(heat_rate))

    return cast(HeatRateResult, {"heat_rate_w": str(heat_rate), "trace": trace.to_dict()})
