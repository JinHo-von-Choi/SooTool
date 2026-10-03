from __future__ import annotations

from decimal import Decimal

import pytest

from sootool.core.errors import SolverBracketError
from sootool.core.solver import bisect, smallest_integer_satisfying


def D(value: str) -> Decimal:
    return Decimal(value)


def test_finds_the_root_of_a_linear_function():
    result = bisect(lambda x: x * 2 - 10, D("0"), D("100"), tolerance=D("0.0001"), max_iter=100)
    assert result.converged
    assert abs(result.x - D("5")) <= D("0.0001")


def test_finds_the_root_of_a_decreasing_function():
    result = bisect(lambda x: 10 - x, D("0"), D("100"), tolerance=D("0.0001"), max_iter=100)
    assert result.converged and abs(result.x - D("10")) <= D("0.0001")


def test_endpoint_root_is_returned_without_iterating():
    result = bisect(lambda x: x - 3, D("3"), D("10"), tolerance=D("0"), max_iter=10)
    assert (result.x, result.iterations, result.converged) == (D("3"), 0, True)


def test_same_sign_at_both_ends_raises_with_details():
    with pytest.raises(SolverBracketError) as info:
        bisect(lambda x: x + 1, D("0"), D("10"), tolerance=D("0.1"), max_iter=10)
    payload = info.value.to_payload()
    assert payload["code"] == "no_sign_change"
    assert payload["details"] == {"lower": "0", "upper": "10", "f_lower": "1", "f_upper": "11"}


def test_invalid_bracket_raises():
    with pytest.raises(SolverBracketError):
        bisect(lambda x: x, D("5"), D("5"), tolerance=D("0"), max_iter=1)


def test_integer_mode_returns_the_nearest_integer_for_a_step_function():
    # 계단 함수: 1000 단위로만 값이 바뀐다. 목표 2500 은 정확히 만들 수 없다.
    step = lambda x: (x // 1000) * 1000 - D("2500")  # noqa: E731
    result = bisect(step, D("0"), D("10000"), tolerance=D("0"), max_iter=100, integer=True)
    assert not result.converged
    assert abs(result.value) == D("500")
    assert result.x == result.x.to_integral_value()


def test_result_is_deterministic():
    f = lambda x: x ** 3 - 20  # noqa: E731
    first  = bisect(f, D("0"), D("10"), tolerance=D("0.000001"), max_iter=100)
    second = bisect(f, D("0"), D("10"), tolerance=D("0.000001"), max_iter=100)
    assert (first.x, first.iterations, first.evaluations) == (second.x, second.iterations, second.evaluations)


def test_iteration_cap_is_respected():
    result = bisect(lambda x: x - D("1") / D("3"), D("0"), D("1"), tolerance=D("0"), max_iter=5)
    assert result.iterations == 5 and not result.converged


# --- smallest_integer_satisfying ---

def test_smallest_integer_is_found_exactly():
    value, calls = smallest_integer_satisfying(lambda x: x >= 12345, 0, 1_000_000)
    assert value == 12345
    assert calls <= 25


def test_lower_bound_that_already_satisfies_is_returned():
    assert smallest_integer_satisfying(lambda x: True, 7, 100) == (7, 1)


def test_unsatisfiable_upper_bound_raises():
    with pytest.raises(SolverBracketError):
        smallest_integer_satisfying(lambda x: x > 10**9, 0, 100)


def test_empty_integer_range_raises():
    with pytest.raises(SolverBracketError):
        smallest_integer_satisfying(lambda x: True, 5, 4)
