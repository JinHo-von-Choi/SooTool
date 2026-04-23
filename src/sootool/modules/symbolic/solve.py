"""symbolic.solve — 방정식 기호 풀이 후 Decimal 재평가 브릿지 (ADR-022).

핵심 경계:
- equation 입력은 `lhs = rhs` 또는 단일식(= 0 가정) 모두 허용.
- AST 화이트리스트 선행 통과 → sympy.sympify(locals={}) → sympy.solve.
- 해 집합은 기호 식 문자열과 Decimal 수치 배열(numeric_eval 시)로 2중 직렬화.
- 복소해·무한해·기호해는 symbolic 배열에만 담기고 solutions 는 실수 Decimal 만.

시그니처:
    solve(equation, var, variables=None, numeric_eval=True)

작성자: 최진호
작성일: 2026-04-24
"""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import DomainConstraintError, InvalidExpressionError
from sootool.core.registry import REGISTRY
from sootool.modules.symbolic import _bridge


def _split_equation(equation: str) -> tuple[str, str]:
    """`lhs = rhs` 형식이면 (lhs, rhs) 반환. 단일식이면 (식, '0')."""
    if equation.count("=") == 0:
        return equation.strip(), "0"
    if equation.count("=") == 1:
        lhs, rhs = equation.split("=", 1)
        lhs, rhs = lhs.strip(), rhs.strip()
        if not lhs or not rhs:
            raise InvalidExpressionError("equation LHS/RHS must be non-empty")
        return lhs, rhs
    raise InvalidExpressionError(
        "equation must contain at most one '=' character",
    )


@REGISTRY.tool(
    namespace="symbolic",
    name="solve",
    description=(
        "방정식 기호 풀이 후 Decimal 재평가. `lhs=rhs` 또는 단일식(=0 가정)을 sympy.solve "
        "로 풀고, variables 치환 시 수치해를 Decimal 문자열로 평가한다."
    ),
    version="1.0.0",
)
def solve(
    equation:     str,
    var:          str,
    variables:    dict[str, str] | None = None,
    numeric_eval: bool                   = True,
) -> dict[str, Any]:
    if not isinstance(equation, str) or not equation.strip():
        raise InvalidExpressionError("equation must be a non-empty string")
    _bridge._validate_var(var)
    bindings = _bridge._validate_variables(variables)

    trace = CalcTrace(tool="symbolic.solve", formula=equation)
    trace.input("equation",     equation)
    trace.input("var",          var)
    trace.input("variables",    dict(bindings))
    trace.input("numeric_eval", numeric_eval)

    lhs_str, rhs_str = _split_equation(equation)
    _bridge._validate_expression(lhs_str, label="equation lhs")
    _bridge._validate_expression(rhs_str, label="equation rhs")

    def _op() -> list[Any]:
        sympy = _bridge._require_sympy()
        lhs = _bridge.sympify_safe(lhs_str)
        rhs = _bridge.sympify_safe(rhs_str)
        expr = lhs - rhs
        # 치환은 미리 적용해 기호 감소(수치해 확보).
        expr_sub = _bridge.substitute(expr, bindings)
        symbol = sympy.Symbol(var)
        solutions = sympy.solve(expr_sub, symbol, dict=False)
        if not isinstance(solutions, list):
            solutions = [solutions]
        return solutions

    raw_solutions = _bridge.run_symbolic(_op)
    trace.step("raw_solution_count", len(raw_solutions))

    symbolic_forms: list[str] = []
    numeric_solutions: list[str] = []

    for sol in raw_solutions:
        symbolic_forms.append(f"{var} = {sol}")
        if not numeric_eval:
            continue
        try:
            evaluated = sol.evalf(50) if hasattr(sol, "evalf") else sol
        except Exception as exc:  # pragma: no cover - defensive
            raise DomainConstraintError(
                f"failed to evaluate symbolic solution {sol!r}: {exc}",
            ) from exc
        # 실수 해만 numeric_solutions 에 담는다. 복소·기호 해는 symbolic 배열만.
        sympy = _bridge._require_sympy()
        if getattr(evaluated, "is_real", None) is True or isinstance(evaluated, (int, float)):
            numeric_solutions.append(_bridge.to_decimal_string(evaluated))
        elif isinstance(evaluated, sympy.Rational):
            numeric_solutions.append(_bridge.to_decimal_string(evaluated))

    trace.step("symbolic_forms", symbolic_forms)
    if numeric_eval:
        trace.step("numeric_solutions", numeric_solutions)
    trace.output({
        "solutions": list(numeric_solutions) if numeric_eval else [],
        "symbolic":  list(symbolic_forms),
    })

    return {
        "solutions": numeric_solutions if numeric_eval else [],
        "symbolic":  symbolic_forms,
        "trace":     trace.to_dict(),
    }
