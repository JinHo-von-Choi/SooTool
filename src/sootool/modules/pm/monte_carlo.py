"""Monte Carlo schedule risk simulation using PERT beta sampling.

내부 자료형 (ADR-008):
- 작업 기간 입력 (O, M, P)는 Decimal 문자열. 내부 float64 샘플링, Decimal 경계 출력.
- 결정론: numpy.random.default_rng(seed) 사용. 기본 seed=0 (ADR-011).

알고리즘:
- 각 task 마다 PERT-Beta 분포 (mean=(O+4M+P)/6, variance=((P-O)/6)^2) 근사하는
  4-parameter Beta(α, β) 에서 샘플링. α=β=6 으로 고정하면 모드 M, 범위 [O, P].
- N회 반복: 각 반복에서 task 기간 합계가 곧 프로젝트 완료 시간.
- 결과: P10 / P50 / P90 퍼센타일 + 평균 + 표준편차.

참고:
- Vose D. Risk Analysis: A Quantitative Guide, 3rd ed., 2008.
- Henderson/Galway (2020), generalized Beta-PERT.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from typing import Any

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

_DEFAULT_N = 1000
_DEFAULT_SEED = 0
_SIG = 10


def _sample_pert_beta(
    rng: np.random.Generator,
    o:   float,
    m:   float,
    p:   float,
    n:   int,
) -> np.ndarray:
    """Sample from the 4-parameter Beta-PERT distribution.

    Shape parameters α, β derived from mode m and range [o, p]:
      α = 1 + 4 (m - o) / (p - o)
      β = 1 + 4 (p - m) / (p - o)
    When p == o, returns o.
    """
    if p == o:
        return np.full(n, o, dtype=np.float64)
    alpha = 1.0 + 4.0 * (m - o) / (p - o)
    beta_ = 1.0 + 4.0 * (p - m) / (p - o)
    # Guard against invalid shape parameters
    alpha = max(alpha, 0.001)
    beta_ = max(beta_, 0.001)
    samples = rng.beta(alpha, beta_, size=n)
    return o + samples * (p - o)


@REGISTRY.tool(
    namespace="pm",
    name="monte_carlo_schedule",
    description=(
        "몬테카를로 일정 시뮬레이션. 각 task (optimistic, most_likely, pessimistic) 를 "
        "Beta-PERT 분포로 n회 샘플링하여 프로젝트 완료 시간의 P10/P50/P90 산출. "
        "결정론적: seed (기본 0)."
    ),
    version="1.0.0",
)
def monte_carlo_schedule(
    tasks:  list[dict[str, str]],
    n:      int = _DEFAULT_N,
    seed:   int = _DEFAULT_SEED,
) -> dict[str, Any]:
    """Monte Carlo sum-of-durations simulation.

    Args:
        tasks: [{"id": str, "optimistic": str, "most_likely": str, "pessimistic": str}, ...]
        n:     Number of simulations. Must be >= 100.
        seed:  RNG seed for determinism.

    Returns:
        {p10, p50, p90, mean, stdev, n, seed, trace}
    """
    trace = CalcTrace(
        tool="pm.monte_carlo_schedule",
        formula="T = Σ_i X_i, X_i ~ BetaPERT(O_i, M_i, P_i); percentiles over n samples",
    )
    if not isinstance(tasks, list) or not tasks:
        raise InvalidInputError("tasks는 비어있지 않은 리스트여야 합니다.")
    if not isinstance(n, int) or isinstance(n, bool) or n < 100:
        raise InvalidInputError(f"n은 100 이상의 정수여야 합니다: {n}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise InvalidInputError(f"seed는 정수여야 합니다: {seed!r}")

    parsed: list[tuple[float, float, float]] = []
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise InvalidInputError(f"tasks[{i}]는 dict 여야 합니다.")
        for k in ("optimistic", "most_likely", "pessimistic"):
            if k not in task:
                raise InvalidInputError(f"tasks[{i}]에 '{k}' 누락.")
        try:
            o = decimal_to_float64(D(task["optimistic"]))
            m = decimal_to_float64(D(task["most_likely"]))
            p = decimal_to_float64(D(task["pessimistic"]))
        except Exception as exc:
            raise InvalidInputError(
                f"tasks[{i}]의 수치는 Decimal 문자열이어야 합니다."
            ) from exc
        if not (o <= m <= p):
            raise DomainConstraintError(
                f"tasks[{i}]: optimistic({o}) <= most_likely({m}) <= pessimistic({p}) 조건 위반."
            )
        parsed.append((o, m, p))

    trace.input("tasks_count", len(parsed))
    trace.input("n", n)
    trace.input("seed", seed)

    rng = np.random.default_rng(seed)
    totals = np.zeros(n, dtype=np.float64)
    for (o, m, p) in parsed:
        samples = _sample_pert_beta(rng, o, m, p, n)
        totals += samples

    p10 = float(np.percentile(totals,  10))
    p50 = float(np.percentile(totals,  50))
    p90 = float(np.percentile(totals,  90))
    mean_val = float(np.mean(totals))
    std_val  = float(np.std(totals, ddof=1))

    out = {
        "p10":   float64_to_decimal_str(p10,      digits=_SIG),
        "p50":   float64_to_decimal_str(p50,      digits=_SIG),
        "p90":   float64_to_decimal_str(p90,      digits=_SIG),
        "mean":  float64_to_decimal_str(mean_val, digits=_SIG),
        "stdev": float64_to_decimal_str(std_val,  digits=_SIG),
    }
    trace.step("p10",  out["p10"])
    trace.step("p50",  out["p50"])
    trace.step("p90",  out["p90"])
    trace.step("mean", out["mean"])
    trace.output(out)

    return {
        **out,
        "n":     n,
        "seed":  seed,
        "trace": trace.to_dict(),
    }
