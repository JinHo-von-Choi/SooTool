"""core.calc 공개 진입점.
"""
from __future__ import annotations

from typing import Any, NotRequired

from sootool.core.calc._evaluator import (
    _Evaluator,
)
from sootool.core.calc._validate import (
    _count_and_validate,
    _parse,
)
from sootool.core.calc._values import (
    _normalize_result,
)
from sootool.core.errors import (
    DomainConstraintError,
    InvalidExpressionError,
)
from sootool.core.limits import ensure_max
from sootool.core.result_types import ToolResult, Trace


class CalcExpressionTrace(Trace):
    """수식 평가 trace. ``parsed_ast_summary`` 는 trace_level=full 응답에만 남는다."""

    parsed_ast_summary: NotRequired[dict[str, int]]


class CalcResult(ToolResult):
    """core.calc 결과. trace_level=none 이거나 응답 크기 한도로 잘리면 trace 가 없다."""

    result:    str
    trace:     NotRequired[CalcExpressionTrace]
    truncated: NotRequired[bool]


def calc(
    expression:  str,
    variables:   dict[str, str] | None = None,
    precision:   int                   = 50,
    trace_level: str                   = "summary",
) -> dict[str, Any]:
    """AST 기반 안전 수식 평가기.

    args:
        expression:  평가할 수식 문자열.
        variables:   이름 → Decimal 문자열 바인딩. None 이면 상수·숫자 리터럴만 사용.
        precision:   mpmath 작업 정밀도(십진 자릿수). 기본 50. 1 이상이어야 함.
        trace_level: 'summary' / 'full' / 'none'. server.py 의 _apply_trace_level 에서
                     후처리되므로 본 함수는 full 이든 summary 든 동일 trace 를 반환하되,
                     full 일 때만 evaluation_steps 를 채운다.
    returns:
        {"result": Decimal 문자열, "trace": {...}}
    """
    if not isinstance(expression, str):
        raise InvalidExpressionError("expression must be a string")
    if not isinstance(precision, int) or precision < 1:
        raise DomainConstraintError("precision must be a positive integer")
    ensure_max("CALC_PRECISION", precision, "precision")

    bindings: dict[str, str] = dict(variables) if variables else {}
    for k, v in bindings.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise DomainConstraintError(
                "variables must map str → str (Decimal string)",
            )

    tree   = _parse(expression)
    counts = _count_and_validate(tree)

    steps: list[dict[str, Any]] = []
    evaluator = _Evaluator(
        variables   = bindings,
        precision   = precision,
        steps       = steps,
        record_full = trace_level == "full",
    )
    value  = evaluator.evaluate(tree)
    output = _normalize_result(value, precision)

    trace: dict[str, Any] = {
        "tool":                "core.calc",
        "formula":             expression,
        "inputs": {
            "expression": expression,
            "variables":  dict(bindings),
            "precision":  precision,
        },
        "steps":               steps,
        "output":              output,
        "parsed_ast_summary":  counts,
    }

    return {"result": output, "trace": trace}
