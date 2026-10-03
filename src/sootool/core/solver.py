"""결정적 Decimal 이분법 근 찾기.

함수 ``f`` 가 구간 [lower, upper] 에서 부호가 바뀌면 이분법으로 ``f(x) = 0`` 인 x 를 찾는다. 모든 연산이
Decimal 이므로 같은 입력은 같은 반복 경로와 결과를 낸다. 호출 횟수는 ``max_iter`` 로 묶는다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from sootool.core.errors import SolverBracketError

_TWO = Decimal(2)


@dataclass(frozen=True)
class SolveStep:
    iteration: int
    x:         Decimal
    value:     Decimal


@dataclass(frozen=True)
class SolveResult:
    x:           Decimal
    value:       Decimal
    converged:   bool
    iterations:  int
    evaluations: int
    lower:       Decimal
    upper:       Decimal
    steps:       list[SolveStep] = field(default_factory=list)


def bisect(
    f:         Callable[[Decimal], Decimal],
    lower:     Decimal,
    upper:     Decimal,
    *,
    tolerance: Decimal,
    max_iter:  int,
    integer:   bool = False,
) -> SolveResult:
    """[lower, upper] 에서 ``f(x) = 0`` 의 근을 이분법으로 찾는다.

    integer=True 이면 정수 x 만 후보로 하며 구간이 인접한 두 정수로 좁혀지면 |f| 가 작은 쪽을 고른다.
    ``converged`` 는 최종 |f(x)| 가 ``tolerance`` 이하인지를 뜻한다. 단계별 함수(세금 구간 등)는 정확히 0 이
    되는 x 가 없을 수 있어 가장 가까운 x 와 잔차를 돌려준다.
    """
    if lower >= upper:
        raise SolverBracketError("lower 는 upper 보다 작아야 합니다.", lower, upper, None, None)
    if integer:
        lower = lower.to_integral_value(rounding="ROUND_CEILING")
        upper = upper.to_integral_value(rounding="ROUND_FLOOR")
        if lower > upper:
            raise SolverBracketError("정수 구간이 비어 있습니다.", lower, upper, None, None)

    f_lower = f(lower)
    evaluations = 1
    if abs(f_lower) <= tolerance:
        return SolveResult(lower, f_lower, True, 0, evaluations, lower, lower)
    f_upper = f(upper)
    evaluations += 1
    if abs(f_upper) <= tolerance:
        return SolveResult(upper, f_upper, True, 0, evaluations, upper, upper)
    if (f_lower > 0) == (f_upper > 0):
        raise SolverBracketError(
            "구간 양 끝의 함수값 부호가 같아 해가 보장되지 않습니다. lower, upper 를 넓혀 보세요.",
            lower, upper, f_lower, f_upper,
        )

    steps: list[SolveStep] = []
    lo, hi, f_lo = lower, upper, f_lower
    best_x, best_f = (lower, f_lower) if abs(f_lower) <= abs(f_upper) else (upper, f_upper)

    for iteration in range(1, max_iter + 1):
        mid = (lo + hi) / _TWO
        if integer:
            mid = mid.to_integral_value(rounding="ROUND_FLOOR")
            if mid <= lo:
                break
        f_mid = f(mid)
        evaluations += 1
        steps.append(SolveStep(iteration, mid, f_mid))
        if abs(f_mid) < abs(best_f):
            best_x, best_f = mid, f_mid
        if abs(f_mid) <= tolerance:
            return SolveResult(mid, f_mid, True, iteration, evaluations, lo, hi, steps)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
        if hi == lo or (integer and hi - lo <= 1):
            break
    return SolveResult(
        best_x, best_f, abs(best_f) <= tolerance, len(steps), evaluations, lo, hi, steps,
    )


def smallest_integer_satisfying(
    predicate: Callable[[int], bool],
    lower:     int,
    upper:     int,
) -> tuple[int, int]:
    """``predicate`` 가 처음 참이 되는 가장 작은 정수를 이분법으로 찾는다.

    predicate 가 [lower, upper] 에서 거짓에서 참으로 한 번만 바뀐다고(단조) 가정한다. 반환은 (정수, 호출 횟수)다.
    upper 에서도 거짓이면 SolverBracketError 를 낸다.
    """
    if lower > upper:
        raise SolverBracketError("정수 구간이 비어 있습니다.", lower, upper, None, None)
    calls = 1
    if predicate(lower):
        return lower, calls
    calls += 1
    if not predicate(upper):
        raise SolverBracketError(
            "구간의 상한에서도 조건을 만족하지 않습니다. upper 를 넓혀 보세요.", lower, upper, False, False,
        )
    lo, hi = lower, upper          # predicate(lo) 거짓, predicate(hi) 참
    while hi - lo > 1:
        mid = (lo + hi) // 2
        calls += 1
        if predicate(mid):
            hi = mid
        else:
            lo = mid
    return hi, calls
