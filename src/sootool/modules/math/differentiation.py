"""Numerical differentiation: central and 5-point stencil.

내부 자료형 (ADR-008):
- 표현식 평가는 core.calc 의 안전 AST 평가기 경유 (Decimal → float64).
- 결과는 float64 → Decimal 문자열 (12 유효숫자).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.calc import calc as _calc
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_SIG = 12


def _f(expression: str, variable: str, x: float) -> float:
    out = _calc(expression=expression, variables={variable: repr(x)}, precision=15)
    return float(out["result"])


@REGISTRY.tool(
    namespace="math",
    name="diff_central",
    description=(
        "중심 차분법 1차 수치 미분: f'(x) ≈ (f(x+h) - f(x-h)) / (2h). "
        "expression 내 자유 변수는 variable 로 지정."
    ),
    version="1.0.0",
)
def diff_central(
    expression: str,
    x:          str,
    h:          str = "0.001",
    variable:   str = "x",
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.diff_central",
        formula="f'(x) ≈ (f(x+h) - f(x-h)) / (2h)",
    )
    try:
        x_f = decimal_to_float64(D(x))
        h_f = decimal_to_float64(D(h))
    except Exception as exc:
        raise InvalidInputError("x, h는 Decimal 문자열이어야 합니다.") from exc
    if h_f <= 0.0:
        raise DomainConstraintError(f"h는 양수여야 합니다: {h}")

    trace.input("expression", expression)
    trace.input("x", x)
    trace.input("h", h)
    trace.input("variable", variable)

    f_plus  = _f(expression, variable, x_f + h_f)
    f_minus = _f(expression, variable, x_f - h_f)
    deriv   = (f_plus - f_minus) / (2.0 * h_f)

    result_s = float64_to_decimal_str(deriv, digits=_SIG)
    trace.step("f(x+h)", float64_to_decimal_str(f_plus,  digits=_SIG))
    trace.step("f(x-h)", float64_to_decimal_str(f_minus, digits=_SIG))
    trace.step("derivative", result_s)
    trace.output({"result": result_s})

    return {"result": result_s, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="math",
    name="diff_five_point",
    description=(
        "5점 공식 1차 수치 미분: f'(x) ≈ (-f(x+2h) + 8 f(x+h) - 8 f(x-h) + f(x-2h)) / (12 h). "
        "중심 차분 대비 O(h⁴) 정확도."
    ),
    version="1.0.0",
)
def diff_five_point(
    expression: str,
    x:          str,
    h:          str = "0.001",
    variable:   str = "x",
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.diff_five_point",
        formula="f'(x) ≈ (-f(x+2h) + 8 f(x+h) - 8 f(x-h) + f(x-2h)) / (12 h)",
    )
    try:
        x_f = decimal_to_float64(D(x))
        h_f = decimal_to_float64(D(h))
    except Exception as exc:
        raise InvalidInputError("x, h는 Decimal 문자열이어야 합니다.") from exc
    if h_f <= 0.0:
        raise DomainConstraintError(f"h는 양수여야 합니다: {h}")

    trace.input("expression", expression)
    trace.input("x", x)
    trace.input("h", h)
    trace.input("variable", variable)

    f1 = _f(expression, variable, x_f - 2.0 * h_f)
    f2 = _f(expression, variable, x_f - 1.0 * h_f)
    f3 = _f(expression, variable, x_f + 1.0 * h_f)
    f4 = _f(expression, variable, x_f + 2.0 * h_f)
    deriv = (-f4 + 8.0 * f3 - 8.0 * f2 + f1) / (12.0 * h_f)

    result_s = float64_to_decimal_str(deriv, digits=_SIG)
    trace.step("derivative", result_s)
    trace.output({"result": result_s})

    return {"result": result_s, "trace": trace.to_dict()}
