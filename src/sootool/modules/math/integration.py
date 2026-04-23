"""Numerical integration: composite Simpson and Gauss-Legendre quadrature.

내부 자료형 (ADR-008):
- 표현식은 core.calc 의 안전 AST 평가기를 경유하여 Decimal 문자열로 sample.
- 구간 내 n_points 지점에서 평가 후 float64 로 정규화하여 mpmath 로 적분.
- 결과는 float64 를 float64_to_decimal_str 로 Decimal 문자열 복귀.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import threading
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.calc import calc as _calc
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_SIG = 12
_MPDPS = 40
_MP_LOCK = threading.Lock()


def _eval_expr_at(expression: str, variable: str, x_val: float) -> float:
    """Evaluate expression at x via core.calc (safe). precision=15 로 float64 과 정합."""
    out = _calc(expression=expression, variables={variable: repr(x_val)}, precision=15)
    return float(out["result"])


def _parse_bounds(a: str, b: str) -> tuple[float, float]:
    try:
        a_f = decimal_to_float64(D(a))
        b_f = decimal_to_float64(D(b))
    except Exception as exc:
        raise InvalidInputError(f"구간 a, b는 Decimal 문자열이어야 합니다: {a!r}, {b!r}") from exc
    if a_f == b_f:
        raise DomainConstraintError("a == b: 구간 길이가 0입니다.")
    if a_f > b_f:
        raise DomainConstraintError(f"a({a}) <= b({b}) 여야 합니다.")
    return a_f, b_f


@REGISTRY.tool(
    namespace="math",
    name="integrate_simpson",
    description=(
        "합성 심프슨 법 수치적분. n은 짝수, 2 이상. "
        "expression 내 자유 변수는 variable 로 지정."
    ),
    version="1.0.0",
)
def integrate_simpson(
    expression: str,
    a:          str,
    b:          str,
    n:          int = 100,
    variable:   str = "x",
) -> dict[str, Any]:
    """Composite Simpson's 1/3 rule.

    Args:
        expression: 피적분 함수 (core.calc 문법).
        a:          적분 하한 (Decimal string).
        b:          적분 상한 (Decimal string).
        n:          부구간 수 (짝수, >=2).
        variable:   자유 변수 이름.

    Returns:
        {result: str, n: int, trace}
    """
    trace = CalcTrace(
        tool="math.integrate_simpson",
        formula="∫ f(x) dx ≈ (h/3) * (f₀ + 4Σf_odd + 2Σf_even + f_n), h=(b-a)/n",
    )
    if not isinstance(n, int) or n < 2 or n % 2 != 0:
        raise InvalidInputError(f"n은 2 이상의 짝수여야 합니다: {n}")
    a_f, b_f = _parse_bounds(a, b)
    h = (b_f - a_f) / n

    trace.input("expression", expression)
    trace.input("a", a)
    trace.input("b", b)
    trace.input("n", n)
    trace.input("variable", variable)

    total = _eval_expr_at(expression, variable, a_f) + _eval_expr_at(expression, variable, b_f)
    for i in range(1, n):
        xi = a_f + i * h
        fi = _eval_expr_at(expression, variable, xi)
        total += (4.0 if i % 2 == 1 else 2.0) * fi

    result_f = total * h / 3.0
    result_s = float64_to_decimal_str(result_f, digits=_SIG)
    trace.step("h", float64_to_decimal_str(h, digits=_SIG))
    trace.step("integral", result_s)
    trace.output({"result": result_s})

    return {"result": result_s, "n": n, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="math",
    name="integrate_gauss_legendre",
    description=(
        "가우스-르장드르 구적법 수치적분. mpmath.quad 경유, degree(노드 수) 기본 20."
    ),
    version="1.0.0",
)
def integrate_gauss_legendre(
    expression: str,
    a:          str,
    b:          str,
    degree:     int = 20,
    variable:   str = "x",
) -> dict[str, Any]:
    """Gauss-Legendre quadrature via mpmath."""
    trace = CalcTrace(
        tool="math.integrate_gauss_legendre",
        formula="∫_a^b f(x) dx = Σ w_i f(x_i) with Legendre nodes",
    )
    if not isinstance(degree, int) or degree < 2:
        raise InvalidInputError(f"degree는 2 이상의 정수여야 합니다: {degree}")
    a_f, b_f = _parse_bounds(a, b)

    trace.input("expression", expression)
    trace.input("a", a)
    trace.input("b", b)
    trace.input("degree", degree)
    trace.input("variable", variable)

    def _f(x_mpf: Any) -> Any:
        y = _eval_expr_at(expression, variable, float(x_mpf))
        return mpmath.mpf(y)

    with _MP_LOCK, mpmath.workdps(_MPDPS):
        val = mpmath.quadgl(_f, [mpmath.mpf(a_f), mpmath.mpf(b_f)], degree=degree)
    result_s = float64_to_decimal_str(float(val), digits=_SIG)
    trace.step("integral", result_s)
    trace.output({"result": result_s})

    return {"result": result_s, "degree": degree, "trace": trace.to_dict()}
