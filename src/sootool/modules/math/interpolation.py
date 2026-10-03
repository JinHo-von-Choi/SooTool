"""Numerical interpolation: linear and cubic spline.

내부 자료형 (ADR-008):
- 샘플 (xs, ys) 입력은 Decimal 문자열 리스트.
- 내부 계산은 numpy/scipy.interpolate (float64).
- 결과는 float64 → Decimal 문자열 (12 유효숫자).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.lazy import lazy_module
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

scipy_interpolate = lazy_module("scipy.interpolate")

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


class InterpolateLinearResult(TracedResult):
    result: str


@REGISTRY.tool(
    namespace="math",
    name="interpolate_linear",
    description=(
        "표본점 (xs, ys) 를 직선으로 이어 x_query 에서의 값을 구하는 1차원 선형 보간이다. "
        "xs 는 엄격히 증가하는 2개 이상의 Decimal 문자열 리스트, ys 는 같은 길이. x_query 가 [min(xs), max(xs)] 밖이면 외삽하지 않고 오류를 낸다. "
        "float64 계산, 유효숫자 12자리."
    ),
    version="1.0.0",
)
def interpolate_linear(
    xs:      list[str],
    ys:      list[str],
    x_query: str,
) -> InterpolateLinearResult:
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


class InterpolateCubicSplineResult(TracedResult):
    result: str


@REGISTRY.tool(
    namespace="math",
    name="interpolate_cubic_spline",
    description=(
        "3차 스플라인 보간(scipy CubicSpline)으로 x_query 에서의 값을 구한다. "
        "xs 는 엄격히 증가하는 4개 이상의 Decimal 문자열 리스트, ys 는 같은 길이. bc_type 은 natural(기본), clamped, not-a-knot 중 하나. x_query 가 표본 구간 밖이면 외삽하지 않고 오류를 낸다. "
        "유효숫자 12자리."
    ),
    version="1.0.0",
)
def interpolate_cubic_spline(
    xs:      list[str],
    ys:      list[str],
    x_query: str,
    bc_type: str = "natural",
) -> InterpolateCubicSplineResult:
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

    cs = scipy_interpolate.CubicSpline(xs_arr, ys_arr, bc_type=bc_type)
    y_val = float(cs(xq))
    y_str = float64_to_decimal_str(y_val, digits=_SIG)
    trace.step("y", y_str)
    trace.output({"result": y_str})

    return {"result": y_str, "trace": trace.to_dict()}
