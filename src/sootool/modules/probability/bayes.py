"""Probability Bayes theorem tool.

내부 자료형: Decimal 전 구간.
posterior = prior * likelihood / marginal (P(A|B) = P(A)*P(B|A) / P(B))
모든 입력은 [0, 1] 범위로 검증.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


class BayesResult(TracedResult):
    """사후확률 P(A|B). Decimal 문자열."""

    posterior: str


def _parse_probability(value: str, name: str) -> Decimal:
    try:
        p = D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc
    if p < D("0") or p > D("1"):
        raise DomainConstraintError(f"{name}={value}은(는) [0, 1] 범위를 벗어납니다.")
    return p


@REGISTRY.tool(
    namespace="probability",
    name="bayes",
    description="베이즈 정리로 사후확률 P(A|B) = P(A)P(B|A)/P(B)를 구한다. prior, likelihood, marginal 은 [0, 1] 구간 십진 문자열이고 marginal 은 0 이 될 수 없으며 Decimal 50자리 정밀도로 계산한다. 입력 간 정합성(P(B) ≥ P(A)P(B|A))은 검사하지 않으므로 marginal 은 전체 확률 법칙으로 먼저 구해야 한다.",
    version="1.0.0",
)
def bayes(
    prior: str,
    likelihood: str,
    marginal: str,
) -> BayesResult:
    """Apply Bayes' theorem to compute the posterior probability.

    posterior = prior * likelihood / marginal
    P(A|B)    = P(A)  * P(B|A)    / P(B)

    Args:
        prior:      P(A)    — prior probability of the hypothesis (Decimal string in [0,1]).
        likelihood: P(B|A)  — probability of evidence given hypothesis (Decimal string in [0,1]).
        marginal:   P(B)    — total probability of evidence (Decimal string in (0,1]).

    Returns:
        {posterior: str, trace}
    """
    trace = CalcTrace(
        tool="probability.bayes",
        formula="P(A|B) = P(A) * P(B|A) / P(B)",
    )

    p_a   = _parse_probability(prior,      "prior")
    p_b_a = _parse_probability(likelihood, "likelihood")
    p_b   = _parse_probability(marginal,   "marginal")

    if p_b == D("0"):
        raise DomainConstraintError("marginal P(B)은 0이 될 수 없습니다 (분모).")

    trace.input("prior (P(A))",       str(p_a))
    trace.input("likelihood (P(B|A))", str(p_b_a))
    trace.input("marginal (P(B))",     str(p_b))

    numerator = p_a * p_b_a
    posterior  = numerator / p_b

    trace.step("numerator = P(A)*P(B|A)", str(numerator))
    trace.step("posterior = numerator / P(B)", str(posterior))
    trace.output({"posterior": str(posterior)})

    return {"posterior": str(posterior), "trace": trace.to_dict()}
