"""Tests for symbolic.diff (ADR-022)."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.symbolic  # noqa: F401
from sootool.core.errors import (
    DisallowedOperationError,
    DomainConstraintError,
    InvalidExpressionError,
)
from sootool.core.registry import REGISTRY


def _diff(**kwargs: object) -> dict[str, object]:
    return REGISTRY.invoke("symbolic.diff", **kwargs)


_MALICIOUS_INPUTS: list[str] = [
    '__import__("os")',
    '__import__("sys").modules',
    "ev" + 'al("1+1")',
    "ex" + 'ec("print(1)")',
    "comp" + 'ile("x", "<s>", "eval")',
    "globals()",
    "lambda x: x",
    "(lambda y: y)(2)",
    "x.__class__",
    "x[0]",
    "[1, 2, 3][0]",
    "{1: 2}[1]",
]


class TestDiffPolynomial:
    def test_polynomial_first_order(self) -> None:
        # d/dx (x^3 + 2x^2 + x + 1) = 3x^2 + 4x + 1
        r = _diff(expression="x**3 + 2*x**2 + x + 1", var="x")
        # sympy 형식(정규화)으로 비교: derivative 문자열에 주요 항이 포함되는지 검증
        d = r["derivative"]
        assert "x**2" in d or "x*" in d
        assert r["numeric"] is None  # variables 없으므로 수치 평가 생략

    def test_polynomial_evaluated_at_point(self) -> None:
        # d/dx (x^3) = 3x^2, x=2 → 12
        r = _diff(expression="x**3", var="x", variables={"x": "2"})
        assert Decimal(r["numeric"]) == Decimal("12")

    def test_polynomial_second_order(self) -> None:
        # d^2/dx^2 (x^3) = 6x, x=2 → 12
        r = _diff(expression="x**3", var="x", order=2, variables={"x": "2"})
        assert Decimal(r["numeric"]) == Decimal("12")

    def test_polynomial_high_order_zero(self) -> None:
        # d^5/dx^5 (x^3) = 0
        r = _diff(expression="x**3", var="x", order=5, variables={"x": "1"})
        assert Decimal(r["numeric"]) == Decimal("0")


class TestDiffTrigonometric:
    def test_sin_at_zero(self) -> None:
        # d/dx sin(x) = cos(x), at x=0 → 1
        r = _diff(expression="sin(x)", var="x", variables={"x": "0"})
        assert abs(Decimal(r["numeric"]) - Decimal("1")) < Decimal("1E-40")

    def test_cos_at_zero(self) -> None:
        # d/dx cos(x) = -sin(x), at x=0 → 0
        r = _diff(expression="cos(x)", var="x", variables={"x": "0"})
        assert abs(Decimal(r["numeric"])) < Decimal("1E-40")

    def test_second_derivative_sin(self) -> None:
        # d^2/dx^2 sin(x) = -sin(x), at x=pi/2 → -1
        import math

        x_val = str(Decimal(repr(math.pi)) / Decimal("2"))
        r = _diff(
            expression="sin(x)",
            var="x",
            order=2,
            variables={"x": x_val},
        )
        # 근사값 -1 (pi 근사로 인한 오차 허용)
        assert abs(Decimal(r["numeric"]) - Decimal("-1")) < Decimal("1E-10")


class TestDiffComposite:
    def test_composite_function(self) -> None:
        # d/dx sin(x^2) = 2x*cos(x^2), at x=0 → 0
        r = _diff(expression="sin(x**2)", var="x", variables={"x": "0"})
        assert abs(Decimal(r["numeric"])) < Decimal("1E-40")

    def test_exp_log_composite(self) -> None:
        # d/dx log(exp(x)) = 1 (identity). 실수 경로로 evaluation.
        r = _diff(expression="log(exp(x))", var="x", variables={"x": "3"})
        # sympy 가 log(exp(x)) 를 x 로 단순화 → 도함수 1
        assert Decimal(r["numeric"]) == Decimal("1")


class TestDiffValidation:
    def test_empty_expression_rejected(self) -> None:
        with pytest.raises(InvalidExpressionError):
            _diff(expression="", var="x")

    def test_non_string_expression_rejected(self) -> None:
        with pytest.raises(InvalidExpressionError):
            _diff(expression=42, var="x")  # type: ignore[arg-type]

    def test_zero_order_rejected(self) -> None:
        with pytest.raises(DomainConstraintError):
            _diff(expression="x**2", var="x", order=0)

    def test_negative_order_rejected(self) -> None:
        with pytest.raises(DomainConstraintError):
            _diff(expression="x**2", var="x", order=-1)

    def test_bool_order_rejected(self) -> None:
        with pytest.raises(DomainConstraintError):
            _diff(expression="x**2", var="x", order=True)  # type: ignore[arg-type]

    def test_huge_order_rejected(self) -> None:
        with pytest.raises(DomainConstraintError):
            _diff(expression="x**2", var="x", order=999)

    def test_bad_var_rejected(self) -> None:
        with pytest.raises((DomainConstraintError, InvalidExpressionError)):
            _diff(expression="x**2", var="1x")

    def test_bad_variable_value_rejected(self) -> None:
        with pytest.raises(DomainConstraintError):
            _diff(
                expression="x**2",
                var="x",
                variables={"x": "not-a-number"},
            )


class TestDiffMalicious:
    @pytest.mark.parametrize("expression", _MALICIOUS_INPUTS)
    def test_malicious_rejected(self, expression: str) -> None:
        with pytest.raises((DisallowedOperationError, InvalidExpressionError)):
            _diff(expression=expression, var="x")

    def test_attribute_access_rejected(self) -> None:
        with pytest.raises(DisallowedOperationError):
            _diff(expression="x.conjugate()", var="x")

    def test_subscript_rejected(self) -> None:
        with pytest.raises(DisallowedOperationError):
            _diff(expression="x[0] + 1", var="x")


class TestDiffNumericEvalFalse:
    def test_numeric_eval_false_skips_numeric(self) -> None:
        r = _diff(
            expression="x**3",
            var="x",
            variables={"x": "2"},
            numeric_eval=False,
        )
        assert r["numeric"] is None
        assert "x**2" in r["derivative"] or "x*" in r["derivative"]


class TestDiffRaceFree:
    def test_diff_race_free(self) -> None:
        baseline = _diff(
            expression="x**3 + 2*x",
            var="x",
            variables={"x": "3"},
        )["numeric"]

        def run() -> str:
            return _diff(
                expression="x**3 + 2*x",
                var="x",
                variables={"x": "3"},
            )["numeric"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
