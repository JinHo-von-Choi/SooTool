"""Probability combinatorics tools: factorial, nCr, nPr.

내부 자료형: 정수 연산.
- n < 1000: math.factorial (표준 라이브러리, CPython bigint)
- n >= 1000: mpmath.factorial (임의 정밀도)
결과는 str 직렬화.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import math
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_MPMATH_FACTORIAL_THRESHOLD = 1000


def _validate_non_negative_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f"{name}은(는) 정수여야 합니다: {value!r}")
    if value < 0:
        raise DomainConstraintError(f"{name}은(는) 음수가 될 수 없습니다: {value}")


def _factorial_int(n: int) -> int:
    """Compute n! as a Python int. Uses mpmath for large n >= threshold."""
    if n < _MPMATH_FACTORIAL_THRESHOLD:
        return math.factorial(n)
    # Compute required decimal digits: log10(n!) ≈ n*log10(n/e) + ...
    # Use Stirling upper bound: ceil(n * log10(n) - n * log10(e) + 1) + margin
    import math as _math
    required_digits = int(_math.ceil(n * _math.log10(n + 1))) + 50
    with mpmath.workdps(required_digits + 20):
        result_mpf = mpmath.factorial(n)
        # Convert to exact integer via floor rounding (n! is always integer)
        return int(mpmath.floor(result_mpf + mpmath.mpf("0.5")))


@REGISTRY.tool(
    namespace="probability",
    name="factorial",
    description="n! 계산. n<1000은 math.factorial, 그 이상은 mpmath 고정밀 연산.",
    version="1.0.0",
)
def factorial(n: int) -> dict[str, Any]:
    """Compute n! (factorial).

    Args:
        n: Non-negative integer.

    Returns:
        {result: str (big integer), trace}
    """
    trace = CalcTrace(tool="probability.factorial", formula="n!")
    _validate_non_negative_int(n, "n")
    trace.input("n", n)

    result = _factorial_int(n)
    result_str = str(result)

    trace.step("engine", "math.factorial" if n < _MPMATH_FACTORIAL_THRESHOLD else "mpmath.factorial")
    trace.step("result", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="probability",
    name="nCr",
    description="이항계수 C(n, r) = n! / (r! * (n-r)!). math.comb 사용.",
    version="1.0.0",
)
def nCr(n: int, r: int) -> dict[str, Any]:
    """Compute the binomial coefficient C(n, r).

    Args:
        n: Total items (non-negative integer).
        r: Items chosen (non-negative integer, r <= n).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(tool="probability.nCr", formula="n! / (r! * (n-r)!)")
    _validate_non_negative_int(n, "n")
    _validate_non_negative_int(r, "r")
    if r > n:
        raise DomainConstraintError(f"r({r})은(는) n({n})을 초과할 수 없습니다.")

    trace.input("n", n)
    trace.input("r", r)

    result = math.comb(n, r)
    result_str = str(result)

    trace.step("result", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="probability",
    name="nPr",
    description="순열 P(n, r) = n! / (n-r)!. math.perm 사용.",
    version="1.0.0",
)
def nPr(n: int, r: int) -> dict[str, Any]:
    """Compute the permutation P(n, r).

    Args:
        n: Total items (non-negative integer).
        r: Items chosen (non-negative integer, r <= n).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(tool="probability.nPr", formula="n! / (n-r)!")
    _validate_non_negative_int(n, "n")
    _validate_non_negative_int(r, "r")
    if r > n:
        raise DomainConstraintError(f"r({r})은(는) n({n})을 초과할 수 없습니다.")

    trace.input("n", n)
    trace.input("r", r)

    result = math.perm(n, r)
    result_str = str(result)

    trace.step("result", result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}
