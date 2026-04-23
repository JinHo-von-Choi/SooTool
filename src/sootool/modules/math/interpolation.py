"""Numerical interpolation: linear and cubic spline.

내부 자료형 (ADR-008):
- 샘플 (xs, ys) 입력은 Decimal 문자열 리스트.
- 내부 계산은 numpy/scipy.interpolate (float64).
- 결과는 float64 → Decimal 문자열 (12 유효숫자).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import CubicSpline

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_SIG = 12


def _to_float_array(values: list[str], name: str) -> np.ndarray:
    if not isinstance(values, list) or not values:
        raise InvalidInputError(f"{name}은(는) 비어있지 않은 리스트여야 합니다.")
    try:
        return np.array([decimal_to_float64(D(v)) for v in values], dtype=np.float64)
    except Exception as exc:
        raise InvalidInputError(f"{name} 요소는 Decimal 문자열이어야 합니다.") from exc


def _parse_query(x_query: str, name: str = "x_query") -> float:
    try:
        return decimal_to_float64(D(x_query))
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) Decimal 문자열이어야 합니다: {x_query!r}") from exc


def _validate_strictly_increasing(xs: np.ndarray) -> None:
    if np.any(np.diff(xs) <= 0):
        raise DomainConstraintError("xs는 엄격히 증가해야 합니다.")


@REGISTRY.tool(
    namespace="math",
    name="interpolate_linear",
    description=(
        "1차원 선형 보간. (xs, ys) 샘플을 받아 x_query 위치의 y 를 반환. "
        "xs 는 엄격히 증가해야 하며, x_query 는 [min(xs), max(xs)] 구간 내."
    ),
    version="1.0.0",
)
def interpolate_linear(
    xs:      list[str],
    ys:      list[str],
    x_query: str,
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.interpolate_linear",
        formula="y(x) = y_i + (y_{i+1} - y_i) * (x - x_i) / (x_{i+1} - x_i)",
    )
    xs_arr = _to_float_array(xs, "xs")
    ys_arr = _to_float_array(ys, "ys")
    if xs_arr.shape != ys_arr.shape:
        raise InvalidInputError(
            f"xs({len(xs_arr)}) 와 ys({len(ys_arr)}) 길이가 같아야 합니다."
        )
    if xs_arr.size < 2:
        raise InvalidInputError("xs/ys는 최소 2개 샘플이어야 합니다.")
    _validate_strictly_increasing(xs_arr)

    xq = _parse_query(x_query)
    if xq < xs_arr[0] or xq > xs_arr[-1]:
        raise DomainConstraintError(
            f"x_query={x_query}은(는) 보간 구간 [{xs_arr[0]}, {xs_arr[-1]}] 밖입니다."
        )

    trace.input("xs", xs)
    trace.input("ys", ys)
    trace.input("x_query", x_query)

    y_val = float(np.interp(xq, xs_arr, ys_arr))
    y_str = float64_to_decimal_str(y_val, digits=_SIG)
    trace.step("y", y_str)
    trace.output({"result": y_str})

    return {"result": y_str, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="math",
    name="interpolate_cubic_spline",
    description=(
        "3차 스플라인 보간 (자연 경계조건 기본). (xs, ys) 샘플을 받아 x_query 에서의 값 반환. "
        "scipy.interpolate.CubicSpline 기반, bc_type='natural'."
    ),
    version="1.0.0",
)
def interpolate_cubic_spline(
    xs:      list[str],
    ys:      list[str],
    x_query: str,
    bc_type: str = "natural",
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.interpolate_cubic_spline",
        formula="Piecewise cubic polynomial S_i(x) with C^2 continuity",
    )
    xs_arr = _to_float_array(xs, "xs")
    ys_arr = _to_float_array(ys, "ys")
    if xs_arr.shape != ys_arr.shape:
        raise InvalidInputError(
            f"xs({len(xs_arr)}) 와 ys({len(ys_arr)}) 길이가 같아야 합니다."
        )
    if xs_arr.size < 4:
        raise InvalidInputError("3차 스플라인은 최소 4개 샘플이 필요합니다.")
    _validate_strictly_increasing(xs_arr)

    valid_bc = {"natural", "clamped", "not-a-knot"}
    if bc_type not in valid_bc:
        raise InvalidInputError(f"bc_type 은 {sorted(valid_bc)} 중 하나여야 합니다.")

    xq = _parse_query(x_query)
    if xq < xs_arr[0] or xq > xs_arr[-1]:
        raise DomainConstraintError(
            f"x_query={x_query}은(는) 보간 구간 [{xs_arr[0]}, {xs_arr[-1]}] 밖입니다."
        )

    trace.input("xs", xs)
    trace.input("ys", ys)
    trace.input("x_query", x_query)
    trace.input("bc_type",  bc_type)

    cs = CubicSpline(xs_arr, ys_arr, bc_type=bc_type)
    y_val = float(cs(xq))
    y_str = float64_to_decimal_str(y_val, digits=_SIG)
    trace.step("y", y_str)
    trace.output({"result": y_str})

    return {"result": y_str, "trace": trace.to_dict()}
