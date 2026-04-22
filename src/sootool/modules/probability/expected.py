"""Probability expected value tool.

내부 자료형: Decimal 전 구간.
E[X] = Σ (value_i * probability_i)
확률 합계가 1 ± 허용 오차(1e-9) 내에 있는지 검증.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_PROB_SUM_TOLERANCE = D("1E-9")


def _parse_decimal(value: str, name: str) -> Decimal:
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="probability",
    name="expected_value",
    description="기댓값: E[X] = Σ(value_i * prob_i). 확률 합계 = 1 검증.",
    version="1.0.0",
)
def expected_value(
    values: list[str],
    probabilities: list[str],
) -> dict[str, Any]:
    """Compute the expected value of a discrete random variable.

    Args:
        values:        List of outcome values as Decimal strings.
        probabilities: List of corresponding probabilities as Decimal strings.
                       Must sum to 1 within tolerance 1e-9.

    Returns:
        {result: str, trace}

    Raises:
        InvalidInputError:      If lists have different lengths or contain invalid numbers.
        DomainConstraintError:  If any probability is outside [0,1] or sum != 1.
    """
    trace = CalcTrace(
        tool="probability.expected_value",
        formula="E[X] = Σ (value_i * prob_i)",
    )

    if len(values) != len(probabilities):
        raise InvalidInputError(
            f"values와 probabilities의 길이가 다릅니다: {len(values)} vs {len(probabilities)}"
        )
    if len(values) == 0:
        raise InvalidInputError("values와 probabilities는 비어 있을 수 없습니다.")

    parsed_vals  = [_parse_decimal(v, f"values[{i}]")   for i, v in enumerate(values)]
    parsed_probs = [_parse_decimal(p, f"probabilities[{i}]") for i, p in enumerate(probabilities)]

    for i, p in enumerate(parsed_probs):
        if p < D("0") or p > D("1"):
            raise DomainConstraintError(
                f"probabilities[{i}]={p}은(는) [0, 1] 범위를 벗어납니다."
            )

    prob_sum = sum(parsed_probs, D("0"))
    if abs(prob_sum - D("1")) > _PROB_SUM_TOLERANCE:
        raise DomainConstraintError(
            f"확률의 합이 1이 아닙니다: sum={prob_sum} (허용 오차 {_PROB_SUM_TOLERANCE})"
        )

    trace.input("values",        [str(v) for v in parsed_vals])
    trace.input("probabilities",  [str(p) for p in parsed_probs])
    trace.step("prob_sum",        str(prob_sum))

    ev = sum(v * p for v, p in zip(parsed_vals, parsed_probs, strict=True))
    result_str = str(ev)

    trace.step("expected_value",  result_str)
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}
