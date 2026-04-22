"""PM PERT (Program Evaluation and Review Technique) tool.

내부 자료형: Decimal 입력/출력, sqrt는 mpmath 경유.
expected  = (O + 4*M + P) / 6
variance  = ((P - O) / 6) ^ 2
stdev     = sqrt(variance)

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
    namespace="pm",
    name="pert",
    description=(
        "PERT 기법: 기댓값 E=(O+4M+P)/6, 분산 V=((P-O)/6)², 표준편차. "
        "Decimal 정밀 연산, sqrt는 mpmath."
    ),
    version="1.0.0",
)
def pert(
    optimistic: str,
    most_likely: str,
    pessimistic: str,
) -> dict[str, Any]:
    """Compute PERT expected duration, variance, and standard deviation.

    Args:
        optimistic:  Best-case duration estimate (Decimal string).
        most_likely: Most probable duration estimate (Decimal string).
        pessimistic: Worst-case duration estimate (Decimal string).

    Returns:
        {expected: str, variance: str, stdev: str, trace}

    Raises:
        DomainConstraintError: If optimistic > pessimistic.
        InvalidInputError:     On non-numeric inputs.
    """
    trace = CalcTrace(
        tool="pm.pert",
        formula="E=(O+4M+P)/6, V=((P-O)/6)², σ=√V",
    )

    o = _parse_decimal(optimistic,  "optimistic")
    m = _parse_decimal(most_likely, "most_likely")
    p = _parse_decimal(pessimistic, "pessimistic")

    if o > p:
        raise DomainConstraintError(
            f"optimistic({o})은(는) pessimistic({p})을 초과할 수 없습니다."
        )

    trace.input("optimistic",  str(o))
    trace.input("most_likely", str(m))
    trace.input("pessimistic", str(p))

    expected = (o + D("4") * m + p) / D("6")
    trace.step("expected = (O+4M+P)/6", str(expected))

    spread   = (p - o) / D("6")
    variance = spread * spread
    trace.step("spread = (P-O)/6",     str(spread))
    trace.step("variance = spread^2",  str(variance))

    # sqrt via mpmath for precision
    with mpmath.workdps(_MPMATH_DPS):
        stdev_mpf = mpmath.sqrt(mpmath.mpf(str(variance)))
        stdev_dec = mpmath_to_decimal(stdev_mpf, digits=30)
    stdev = str(stdev_dec)
    trace.step("stdev = √variance",    stdev)

    trace.output({
        "expected": str(expected),
        "variance": str(variance),
        "stdev":    stdev,
    })

    return {
        "expected": str(expected),
        "variance": str(variance),
        "stdev":    stdev,
        "trace":    trace.to_dict(),
    }
