"""Tests for symbolic.solve (ADR-022)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

pytest.importorskip("sympy")

import sootool.modules.symbolic  # noqa: F401
from sootool.core.errors import (
    DisallowedOperationError,
    DomainConstraintError,
    InvalidExpressionError,
)
from sootool.core.registry import REGISTRY


def _solve(**kwargs: object) -> dict[str, object]:
    return REGISTRY.invoke("symbolic.solve", **kwargs)


# 악성 입력 세트 — 각 항목은 AST 화이트리스트에서 거부되어야 한다.
_MALICIOUS_INPUTS: list[str] = [
    '__import__("os")',
    '__import__("os").system("ls")',
    "ev" + 'al("1+1")',
    "ex" + 'ec("print(1)")',
    "comp" + 'ile("1", "", "eval")',
    'open("/etc/passwd")',
    "lambda x: x",
    "(lambda: 1)()",
    "x.__class__",
    "x[0]",
    "[1, 2, 3]",
    "{1: 2}",
]


class TestSolveQuadratic:
    def test_quadratic_two_real_roots(self) -> None:
        # x^2 - 2x - 3 = 0 → roots: 3, -1
        r = _solve(equation="x**2 - 2*x - 3", var="x")
        sols = sorted(Decimal(s) for s in r["solutions"])
        assert len(sols) == 2
        assert abs(sols[0] - Decimal("-1")) < Decimal("1E-40")
        assert abs(sols[1] - Decimal("3")) < Decimal("1E-40")
        # symbolic forms 포함
        assert any("-1" in s for s in r["symbolic"])
        assert any("3" in s for s in r["symbolic"])
        assert r["trace"]["tool"] == "symbolic.solve"

    def test_quadratic_equals_form(self) -> None:
        # x^2 = 3 → roots: sqrt(3), -sqrt(3)
        # Decimal.sqrt 는 기본 컨텍스트(28자리) 정밀도이므로 허용오차를 완화.
        from decimal import getcontext

        ctx = getcontext().copy()
        ctx.prec = 60
        r = _solve(equation="x**2 = 3", var="x")
        sols = sorted(Decimal(s) for s in r["solutions"])
        assert len(sols) == 2
        expected = ctx.sqrt(Decimal("3"))
        assert abs(sols[0] - (-expected)) < Decimal("1E-25")
        assert abs(sols[1] - expected) < Decimal("1E-25")


class TestSolveLinear:
    def test_linear_single_root(self) -> None:
        # 2x + 6 = 0 → x = -3
        r = _solve(equation="2*x + 6", var="x")
        assert len(r["solutions"]) == 1
        assert Decimal(r["solutions"][0]) == Decimal("-3")

    def test_linear_with_variables_substitution(self) -> None:
        # a*x + b = 0 with a=2, b=-10 → x = 5
        r = _solve(
            equation="a*x + b",
            var="x",
            variables={"a": "2", "b": "-10"},
        )
        assert len(r["solutions"]) == 1
        assert Decimal(r["solutions"][0]) == Decimal("5")


class TestSolveCubic:
    def test_cubic_three_real_roots(self) -> None:
        # x^3 - 6x^2 + 11x - 6 = 0 → roots: 1, 2, 3
        r = _solve(equation="x**3 - 6*x**2 + 11*x - 6", var="x")
        sols = sorted(Decimal(s) for s in r["solutions"])
        assert len(sols) == 3
        assert abs(sols[0] - Decimal("1")) < Decimal("1E-30")
        assert abs(sols[1] - Decimal("2")) < Decimal("1E-30")
        assert abs(sols[2] - Decimal("3")) < Decimal("1E-30")


class TestSolveComplex:
    def test_complex_roots_symbolic_only(self) -> None:
        # x^2 + 1 = 0 → ±i (실수 해 없음, 기호 해만)
        r = _solve(equation="x**2 + 1", var="x")
        # 실수 해가 없으므로 numeric 배열은 비어 있어야 한다.
        assert r["solutions"] == []
        # symbolic 에는 두 해 모두 포함 (±I)
        assert len(r["symbolic"]) == 2
        joined = "".join(r["symbolic"])
        assert "I" in joined

    def test_numeric_eval_false(self) -> None:
        r = _solve(equation="x**2 - 4", var="x", numeric_eval=False)
        assert r["solutions"] == []
        assert len(r["symbolic"]) == 2


class TestSolveNoSolution:
    def test_no_solution_trivial(self) -> None:
        # 1 = 2 → sympy 는 빈 리스트 반환
        r = _solve(equation="1 - 2", var="x")
        assert r["solutions"] == []
        assert r["symbolic"] == []


class TestSolveMalicious:
    """AST 화이트리스트가 위험 노드를 봉쇄하는지 확인."""

    @pytest.mark.parametrize("equation", _MALICIOUS_INPUTS)
    def test_malicious_rejected(self, equation: str) -> None:
        with pytest.raises((DisallowedOperationError, InvalidExpressionError)):
            _solve(equation=equation, var="x")

    def test_attribute_access_rejected(self) -> None:
        with pytest.raises(DisallowedOperationError):
            _solve(equation="x.conjugate()", var="x")


class TestSolveValidation:
    def test_empty_equation_rejected(self) -> None:
        with pytest.raises(InvalidExpressionError):
            _solve(equation="", var="x")

    def test_non_string_equation_rejected(self) -> None:
        with pytest.raises(InvalidExpressionError):
            _solve(equation=123, var="x")  # type: ignore[arg-type]

    def test_bad_var_rejected(self) -> None:
        with pytest.raises((DomainConstraintError, InvalidExpressionError)):
            _solve(equation="x**2 - 1", var="1x")

    def test_too_many_equals_rejected(self) -> None:
        with pytest.raises(InvalidExpressionError):
            _solve(equation="x = 1 = 2", var="x")

    def test_bad_variable_value_rejected(self) -> None:
        with pytest.raises(DomainConstraintError):
            _solve(
                equation="a*x + 1",
                var="x",
                variables={"a": "not-a-number"},
            )


class TestSolveRaceFree:
    def test_solve_race_free(self) -> None:
        baseline = _solve(equation="x**2 - 2*x - 3", var="x")["solutions"]

        def run() -> list[str]:
            return _solve(equation="x**2 - 2*x - 3", var="x")["solutions"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
