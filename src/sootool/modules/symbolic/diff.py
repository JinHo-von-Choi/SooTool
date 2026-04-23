"""symbolic.diff — n차 기호 미분 후 Decimal 평가 브릿지 (ADR-022).

시그니처:
    diff(expression, var, order=1, variables=None, numeric_eval=True)

- expression 은 AST 화이트리스트 선행 통과 후 sympy.sympify(locals={}) 로 파싱.
- sympy.diff(expr, Symbol(var), order) 로 n차 미분.
- variables 치환 시 Decimal 평가 결과 numeric 필드 포함.
- 반환: {derivative, numeric, trace}

작성자: 최진호
작성일: 2026-04-24
"""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import DomainConstraintError, InvalidExpressionError
from sootool.core.registry import REGISTRY
from sootool.modules.symbolic import _bridge


@REGISTRY.tool(
    namespace="symbolic",
    name="diff",
    description=(
        "n차 기호 미분 후 Decimal 평가. sympy.diff 로 derivative 를 구하고, variables "
        "치환 시 수치 결과를 Decimal 문자열로 반환한다."
    ),
    version="1.0.0",
)
def diff(
    expression:   str,
    var:          str,
    order:        int                     = 1,
    variables:    dict[str, str] | None   = None,
    numeric_eval: bool                    = True,
) -> dict[str, Any]:
    if not isinstance(expression, str) or not expression.strip():
        raise InvalidExpressionError("expression must be a non-empty string")
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        raise DomainConstraintError("order must be a positive integer >= 1")
    if order > 20:
        raise DomainConstraintError("order must be <= 20")
    _bridge._validate_var(var)
    bindings = _bridge._validate_variables(variables)

    trace = CalcTrace(tool="symbolic.diff", formula=f"d^{order}/d{var}^{order} ({expression})")
    trace.input("expression",   expression)
    trace.input("var",          var)
    trace.input("order",        order)
    trace.input("variables",    dict(bindings))
    trace.input("numeric_eval", numeric_eval)

    _bridge._validate_expression(expression)

    def _op() -> Any:
        sympy = _bridge._require_sympy()
        expr = _bridge.sympify_safe(expression)
        symbol = sympy.Symbol(var)
        return sympy.diff(expr, symbol, order)

    derivative = _bridge.run_symbolic(_op)
    derivative_str = str(derivative)
    trace.step("derivative", derivative_str)

    numeric: str | None = None
    if numeric_eval and bindings:
        substituted = _bridge.substitute(derivative, bindings)
        sympy = _bridge._require_sympy()
        evaluated = substituted.evalf(50) if hasattr(substituted, "evalf") else substituted
        if (
            getattr(evaluated, "is_real", None) is True
            or isinstance(evaluated, (int, float))
            or isinstance(evaluated, sympy.Rational)
        ):
            numeric = _bridge.to_decimal_string(evaluated)
        else:
            # 실수가 아닌(기호·복소) 결과는 numeric 필드 None 유지, trace 에만 기록.
            trace.step("numeric_skipped_reason", "non-real evaluation")

    trace.step("numeric", numeric)
    trace.output({"derivative": derivative_str, "numeric": numeric})

    return {
        "derivative": derivative_str,
        "numeric":    numeric,
        "trace":      trace.to_dict(),
    }
