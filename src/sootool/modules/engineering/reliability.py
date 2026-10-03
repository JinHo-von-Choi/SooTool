"""Reliability engineering tools (Tier 3).

Tools:
  - exponential_reliability  : R(t) = exp(−λ t); MTBF = 1/λ
  - series_reliability       : R_sys = Π R_i
  - parallel_reliability     : R_sys = 1 − Π (1 − R_i)
  - weibull_reliability      : R(t) = exp(−(t/η)^β)

ADR-001 Decimal, ADR-003 trace, ADR-007 stateless.
exp·비정수 거듭제곱은 mpmath workdps(50) → mpmath_to_decimal(digits=30).
"""
from __future__ import annotations

from decimal import Decimal
from typing import cast

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_ZERO    = Decimal("0")
_ONE     = Decimal("1")
_MP_DPS  = 50
_OUT_DIG = 30


def _exp_mp(x: Decimal) -> Decimal:
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(mpmath.exp(mpmath.mpf(str(x))), digits=_OUT_DIG)


def _pow_mp(base: Decimal, exponent: Decimal) -> Decimal:
    if base <= _ZERO:
        raise InvalidInputError("거듭제곱의 밑은 0 초과여야 합니다.")
    with mpmath.workdps(_MP_DPS):
        return mpmath_to_decimal(
            mpmath.power(mpmath.mpf(str(base)), mpmath.mpf(str(exponent))),
            digits=_OUT_DIG,
        )


# ---------------------------------------------------------------------------
# Exponential reliability
# ---------------------------------------------------------------------------
class ExponentialReliabilityResult(TracedResult):
    reliability:   str
    unreliability: str
    mtbf:          str


@REGISTRY.tool(
    namespace="engineering",
    name="exponential_reliability",
    description=(
        "지수분포 고장 모델의 신뢰도 R(t) = exp(−λt), 불신뢰도 1−R, 평균 고장간격 MTBF = 1/λ 를 "
        "계산한다. failure_rate λ 는 단위시간당 고장률(0 초과), time 은 같은 시간 단위의 t(0 이상)이며 "
        "시간 단위가 다르면 틀린다. 고장률이 일정한 우발 고장 구간 가정이라 마모 고장에는 "
        "weibull_reliability 를 쓴다. exp 는 30자리 유효숫자."
    ),
    version="1.0.0",
)
def exponential_reliability(
    failure_rate: str,
    time:         str,
) -> ExponentialReliabilityResult:
    """Return reliability at time t and MTBF under exponential failure model."""
    trace = CalcTrace(
        tool="engineering.exponential_reliability",
        formula="R(t) = exp(−λ t); MTBF = 1/λ",
    )
    lam = D(failure_rate)
    t_d = D(time)
    if lam <= _ZERO:
        raise InvalidInputError("failure_rate는 0 초과여야 합니다.")
    if t_d < _ZERO:
        raise InvalidInputError("time은 0 이상이어야 합니다.")

    trace.input("failure_rate", failure_rate)
    trace.input("time",         time)

    exponent = -mul(lam, t_d)
    reliability = _exp_mp(exponent)
    mtbf = div(_ONE, lam)
    unreliability = _ONE - reliability

    trace.step("exponent",    str(exponent))
    trace.step("reliability", str(reliability))
    trace.step("mtbf",        str(mtbf))
    trace.output({
        "reliability":   str(reliability),
        "unreliability": str(unreliability),
        "mtbf":          str(mtbf),
    })

    return cast(ExponentialReliabilityResult, {
        "reliability":   str(reliability),
        "unreliability": str(unreliability),
        "mtbf":          str(mtbf),
        "trace":         trace.to_dict(),
    })


# ---------------------------------------------------------------------------
# Series reliability
# ---------------------------------------------------------------------------
class SystemReliabilityResult(TracedResult):
    reliability: str


@REGISTRY.tool(
    namespace="engineering",
    name="series_reliability",
    description=(
        "직렬 시스템 신뢰도 R_sys = ΠR_i 를 계산한다. component_reliabilities 는 구성요소 신뢰도의 "
        "숫자 문자열 목록(1개 이상, 각 0 이상 1 이하)이며 백분율(99)이 아니라 소수(0.99)로 넣는다. "
        "구성요소가 서로 독립이라고 가정하므로 고장이 연관된 경우에는 맞지 않다. 반올림 없이 "
        "50자리 유효숫자."
    ),
    version="1.0.0",
)
def series_reliability(component_reliabilities: list[str]) -> SystemReliabilityResult:
    """Compute series-system reliability as the product of component reliabilities."""
    trace = CalcTrace(
        tool="engineering.series_reliability",
        formula="R_sys = Π R_i",
    )
    if not component_reliabilities:
        raise InvalidInputError("component_reliabilities는 최소 1개 이상이어야 합니다.")
    values = [D(r) for r in component_reliabilities]
    for i, v in enumerate(values):
        if v < _ZERO or v > _ONE:
            raise InvalidInputError(
                f"component_reliabilities[{i}]는 [0, 1] 범위여야 합니다."
            )

    trace.input("component_reliabilities", component_reliabilities)

    product = _ONE
    for v in values:
        product = mul(product, v)

    trace.step("r_sys", str(product))
    trace.output(str(product))
    return cast(SystemReliabilityResult, {"reliability": str(product), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Parallel reliability
# ---------------------------------------------------------------------------
@REGISTRY.tool(
    namespace="engineering",
    name="parallel_reliability",
    description=(
        "병렬(중복) 시스템 신뢰도 R_sys = 1 − Π(1 − R_i)를 계산한다. component_reliabilities 는 "
        "구성요소 신뢰도의 숫자 문자열 목록(1개 이상, 각 0 이상 1 이하)이며 소수로 넣는다(0.99). "
        "하나라도 작동하면 시스템이 작동하는 구조이며 구성요소가 독립이라고 가정한다. 구성요소 k개 "
        "이상이 필요한 k-of-n 구조에는 쓸 수 없다. 반올림 없이 50자리 유효숫자."
    ),
    version="1.0.0",
)
def parallel_reliability(component_reliabilities: list[str]) -> SystemReliabilityResult:
    """Compute parallel-system reliability (complement of all-fail probability)."""
    trace = CalcTrace(
        tool="engineering.parallel_reliability",
        formula="R_sys = 1 − Π(1 − R_i)",
    )
    if not component_reliabilities:
        raise InvalidInputError("component_reliabilities는 최소 1개 이상이어야 합니다.")
    values = [D(r) for r in component_reliabilities]
    for i, v in enumerate(values):
        if v < _ZERO or v > _ONE:
            raise InvalidInputError(
                f"component_reliabilities[{i}]는 [0, 1] 범위여야 합니다."
            )

    trace.input("component_reliabilities", component_reliabilities)

    fail_product = _ONE
    for v in values:
        fail_product = mul(fail_product, _ONE - v)
    r_sys = _ONE - fail_product

    trace.step("fail_product", str(fail_product))
    trace.step("r_sys",        str(r_sys))
    trace.output(str(r_sys))
    return cast(SystemReliabilityResult, {"reliability": str(r_sys), "trace": trace.to_dict()})


# ---------------------------------------------------------------------------
# Weibull reliability
# ---------------------------------------------------------------------------
class WeibullReliabilityResult(TracedResult):
    reliability:   str
    unreliability: str


@REGISTRY.tool(
    namespace="engineering",
    name="weibull_reliability",
    description=(
        "2모수 와이블 분포의 신뢰도 R(t) = exp(−(t/η)^β)와 불신뢰도를 계산한다. shape β 와 "
        "scale η 는 0 초과, time 은 η 와 같은 단위의 0 이상 값이다(0 이면 R = 1). β < 1 은 초기 "
        "고장, β = 1 은 우발 고장, β > 1 은 마모 고장에 해당한다. 위치모수 γ 는 지원하지 않는다. "
        "거듭제곱과 exp 는 30자리 유효숫자."
    ),
    version="1.0.0",
)
def weibull_reliability(
    shape:  str,
    scale:  str,
    time:   str,
) -> WeibullReliabilityResult:
    """Weibull two-parameter reliability function."""
    trace = CalcTrace(
        tool="engineering.weibull_reliability",
        formula="R(t) = exp(−(t/η)^β)",
    )
    beta = D(shape)
    eta = D(scale)
    t_d = D(time)
    if beta <= _ZERO:
        raise InvalidInputError("shape β는 0 초과여야 합니다.")
    if eta <= _ZERO:
        raise InvalidInputError("scale η는 0 초과여야 합니다.")
    if t_d < _ZERO:
        raise InvalidInputError("time은 0 이상이어야 합니다.")

    trace.input("shape", shape)
    trace.input("scale", scale)
    trace.input("time",  time)

    if t_d == _ZERO:
        reliability = _ONE
        ratio_pow = _ZERO
    else:
        ratio = div(t_d, eta)
        ratio_pow = _pow_mp(ratio, beta)
        reliability = _exp_mp(-ratio_pow)

    unreliability = _ONE - reliability

    trace.step("ratio_power",  str(ratio_pow))
    trace.step("reliability",  str(reliability))
    trace.output({
        "reliability":   str(reliability),
        "unreliability": str(unreliability),
    })

    return cast(WeibullReliabilityResult, {
        "reliability":   str(reliability),
        "unreliability": str(unreliability),
        "trace":         trace.to_dict(),
    })
