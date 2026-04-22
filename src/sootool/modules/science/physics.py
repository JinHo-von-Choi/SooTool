"""Science physics tool: half_life (radioactive decay).

내부 자료형 (ADR-008):
- 입력: Decimal 문자열.
- 지수 연산 (0.5)^(t/T): mpmath 경유.
- 출력: Decimal 문자열.

remaining = initial * (0.5)^(t / T)
fraction  = remaining / initial = (0.5)^(t / T)

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_MPMATH_DPS = 50


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="science",
    name="half_life",
    description=(
        "방사성 붕괴: N(t) = N₀ × (0.5)^(t/T). "
        "mpmath 고정밀 지수 연산. 동일 단위 사용 필수."
    ),
    version="1.0.0",
)
def half_life(
    initial_amount: str,
    half_life: str,
    elapsed_time: str,
) -> dict[str, Any]:
    """Compute radioactive decay using the half-life formula.

    Args:
        initial_amount: Initial quantity N₀ (Decimal string, positive).
        half_life:      Half-life period T (Decimal string, positive, same unit as elapsed_time).
        elapsed_time:   Time elapsed t (Decimal string, non-negative, same unit as half_life).

    Returns:
        {remaining: str, fraction: str, trace}

    Raises:
        DomainConstraintError: If initial_amount <= 0 or half_life <= 0 or elapsed_time < 0.
        InvalidInputError:     On non-numeric inputs.
    """
    trace = CalcTrace(
        tool="science.half_life",
        formula="N(t) = N₀ × (0.5)^(t/T)",
    )

    n0 = _parse_decimal(initial_amount, "initial_amount")
    t  = _parse_decimal(elapsed_time,   "elapsed_time")
    T  = _parse_decimal(half_life,      "half_life")

    if n0 <= D("0"):
        raise DomainConstraintError(f"initial_amount는 양수여야 합니다: {initial_amount}")
    if T <= D("0"):
        raise DomainConstraintError(f"half_life는 양수여야 합니다: {half_life}")
    if t < D("0"):
        raise DomainConstraintError(f"elapsed_time은 음수가 될 수 없습니다: {elapsed_time}")

    trace.input("initial_amount", str(n0))
    trace.input("half_life",      str(T))
    trace.input("elapsed_time",   str(t))

    with mpmath.workdps(_MPMATH_DPS):
        t_over_T = mpmath.mpf(str(t)) / mpmath.mpf(str(T))
        fraction_mpf  = mpmath.power(mpmath.mpf("0.5"), t_over_T)
        remaining_mpf = mpmath.mpf(str(n0)) * fraction_mpf

        fraction_dec  = mpmath_to_decimal(fraction_mpf,  digits=30)
        remaining_dec = mpmath_to_decimal(remaining_mpf, digits=30)

    trace.step("t/T",       str(mpmath.nstr(t_over_T, 15)))
    trace.step("fraction",  str(fraction_dec))
    trace.step("remaining", str(remaining_dec))
    trace.output({"remaining": str(remaining_dec), "fraction": str(fraction_dec)})

    return {
        "remaining": str(remaining_dec),
        "fraction":  str(fraction_dec),
        "trace":     trace.to_dict(),
    }
