"""Geometry vector tools: dot product, cross product, norm (L-p)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_MPMATH_DPS = 50


def _parse_decimal_list(values: list[str], name: str) -> list[Decimal]:
    try:
        return [D(str(v)) for v in values]
    except Exception as exc:
        raise InvalidInputError(f"{name} 변환 오류: {exc}") from exc


@REGISTRY.tool(
    namespace="geometry",
    name="vector_dot",
    description="벡터 내적(dot product). a, b: Decimal 문자열 리스트.",
    version="1.0.0",
)
def vector_dot(a: list[str], b: list[str]) -> dict[str, Any]:
    """Compute the dot product of two vectors: Σ a_i * b_i.

    Args:
        a: First vector as list of Decimal strings.
        b: Second vector as list of Decimal strings (same length as a).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(tool="geometry.vector_dot", formula="Σ a_i * b_i")
    trace.input("a", a)
    trace.input("b", b)

    av = _parse_decimal_list(a, "a")
    bv = _parse_decimal_list(b, "b")

    if len(av) != len(bv):
        raise DomainConstraintError(
            f"벡터 길이가 일치하지 않습니다: len(a)={len(av)}, len(b)={len(bv)}"
        )
    if len(av) == 0:
        raise DomainConstraintError("빈 벡터에는 내적을 계산할 수 없습니다.")

    result = sum((x * y for x, y in zip(av, bv, strict=True)), D("0"))

    trace.step("result", str(result))
    trace.output({"result": str(result)})

    return {"result": str(result), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="geometry",
    name="vector_cross",
    description="3D 벡터 외적(cross product). a, b: 각 3개 원소 Decimal 문자열 리스트.",
    version="1.0.0",
)
def vector_cross(a: list[str], b: list[str]) -> dict[str, Any]:
    """Compute the cross product of two 3D vectors.

    Args:
        a: First 3D vector as list of 3 Decimal strings.
        b: Second 3D vector as list of 3 Decimal strings.

    Returns:
        {result: list[str], trace}
    """
    trace = CalcTrace(
        tool="geometry.vector_cross",
        formula="a × b = (a1b2-a2b1, a2b0-a0b2, a0b1-a1b0)",
    )
    trace.input("a", a)
    trace.input("b", b)

    av = _parse_decimal_list(a, "a")
    bv = _parse_decimal_list(b, "b")

    if len(av) != 3 or len(bv) != 3:
        raise DomainConstraintError(
            f"외적은 3차원 벡터에만 정의됩니다. "
            f"len(a)={len(av)}, len(b)={len(bv)}"
        )

    cx = av[1] * bv[2] - av[2] * bv[1]
    cy = av[2] * bv[0] - av[0] * bv[2]
    cz = av[0] * bv[1] - av[1] * bv[0]

    result = [str(cx), str(cy), str(cz)]

    trace.step("result", result)
    trace.output({"result": result})

    return {"result": result, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="geometry",
    name="vector_norm",
    description="벡터 L-p 노름. v: Decimal 문자열 리스트, p: 정수(기본 2). mpmath sqrt 사용.",
    version="1.0.0",
)
def vector_norm(v: list[str], p: int = 2) -> dict[str, Any]:
    """Compute the L-p norm of a vector: (Σ |v_i|^p)^(1/p).

    Args:
        v: Vector as list of Decimal strings.
        p: Norm order (positive integer, default 2 for Euclidean).

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(
        tool="geometry.vector_norm",
        formula="(Σ |v_i|^p)^(1/p)",
    )
    trace.input("v", v)
    trace.input("p", p)

    if p < 1:
        raise DomainConstraintError(f"p 는 1 이상의 정수여야 합니다: {p}")

    vv = _parse_decimal_list(v, "v")
    if len(vv) == 0:
        raise DomainConstraintError("빈 벡터의 노름은 정의되지 않습니다.")

    with mpmath.workdps(_MPMATH_DPS):
        elements = [mpmath.mpf(str(x)) for x in vv]
        powered  = sum(abs(x) ** p for x in elements)
        norm     = powered ** (mpmath.mpf("1") / mpmath.mpf(str(p)))
        norm_str = mpmath.nstr(norm, 30, strip_zeros=False)

    result = D(norm_str)

    trace.step("sum_powered", str(powered))
    trace.step("norm",        str(result))
    trace.output({"result": str(result)})

    return {"result": str(result), "trace": trace.to_dict()}
