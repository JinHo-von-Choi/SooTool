"""Shared helpers for symbolic.* tools (ADR-022).

설계:
- 표현식 입력은 core.calc._parse + _count_and_validate 로 AST 화이트리스트 선행 검증.
- 화이트리스트 통과 후에만 sympy.sympify(locals={}, rational=False) 호출 — 코드 실행 경로 봉쇄.
- sympy 결과는 evalf(mpmath 기반) → mpmath.mpf → Decimal 문자열로 직렬화.
- 전체 sympy 연산은 시간 제한(5초) 안에서 수행. 초과 시 DomainConstraintError.

작성자: 최진호
작성일: 2026-04-24
"""
from __future__ import annotations

import signal
from collections.abc import Callable
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.calc import _count_and_validate, _parse
from sootool.core.cast import mpmath_to_decimal
from sootool.core.errors import (
    DomainConstraintError,
    InvalidExpressionError,
    SooToolError,
)

# Decimal 직렬화 유효숫자. core.calc 와 동일한 기본 정밀도 50.
_PRECISION = 50

# expression 문자열 상한 (symbolic 한정).
_MAX_EXPR_LEN = 5000

# sympy 평가 timeout (초).
_EVAL_TIMEOUT_S = 5


class SymbolicDependencyError(SooToolError):
    """sympy optional dependency 미설치."""


def _require_sympy() -> Any:
    """sympy 모듈을 지연 import. 없으면 친절한 설치 안내로 실패."""
    try:
        import sympy
    except ImportError as exc:  # pragma: no cover - optional dep absent
        raise SymbolicDependencyError(
            "sympy 가 설치되지 않았습니다. symbolic.* 도구를 사용하려면 "
            "`pip install 'sootool[symbolic]'` 또는 "
            "`uv pip install -e .[symbolic]` 로 optional extra 를 설치하세요.",
        ) from exc
    return sympy


def _validate_expression(expression: str, label: str = "expression") -> None:
    """AST 화이트리스트로 수식 문자열을 사전 검증한다."""
    if not isinstance(expression, str):
        raise InvalidExpressionError(f"{label} must be a string")
    if len(expression) > _MAX_EXPR_LEN:
        raise DomainConstraintError(
            f"{label} length {len(expression)} exceeds limit {_MAX_EXPR_LEN}",
        )
    tree = _parse(expression)
    _count_and_validate(tree)


def _validate_var(var: str) -> None:
    if not isinstance(var, str) or not var:
        raise DomainConstraintError("var must be a non-empty string")
    # AST 평가를 통해 단일 식별자인지 확인 — 단순 정규식보다 안전.
    tree = _parse(var)
    import ast

    body = tree.body
    if not isinstance(body, ast.Name):
        raise DomainConstraintError(f"var must be a single identifier, got {var!r}")


def _validate_variables(variables: dict[str, str] | None) -> dict[str, str]:
    if variables is None:
        return {}
    if not isinstance(variables, dict):
        raise DomainConstraintError("variables must be a dict[str, str]")
    out: dict[str, str] = {}
    for k, v in variables.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise DomainConstraintError(
                "variables must map str → str (Decimal string)",
            )
        _validate_var(k)
        # Decimal 로 파싱 가능한지 확인.
        try:
            Decimal(v)
        except Exception as exc:
            raise DomainConstraintError(
                f"variable {k!r} value is not a valid Decimal string: {v!r}",
            ) from exc
        out[k] = v
    return out


class _EvalTimeout(SooToolError):
    pass


@contextmanager
def _time_limit(seconds: int) -> Any:
    """SIGALRM 기반 단순 타임아웃. 메인 스레드에서만 유효."""
    def _handler(signum: int, frame: Any) -> None:  # noqa: ARG001
        raise _EvalTimeout(f"sympy evaluation exceeded {seconds}s")

    # signal.alarm 은 POSIX·메인 스레드 한정. 지원되지 않는 환경에선 보호 없이 실행.
    has_alarm = hasattr(signal, "SIGALRM")
    if not has_alarm:
        yield
        return
    try:
        previous = signal.signal(signal.SIGALRM, _handler)
    except (ValueError, OSError):
        # 메인 스레드 외에서는 signal.signal 이 실패 — 보호 없이 진행.
        yield
        return
    try:
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def run_symbolic(op: Callable[[], Any]) -> Any:
    """sympy 연산을 timeout 과 ImportError 안내로 감싸 실행한다."""
    _require_sympy()
    try:
        with _time_limit(_EVAL_TIMEOUT_S):
            return op()
    except _EvalTimeout as exc:
        raise DomainConstraintError(str(exc)) from exc


def sympify_safe(expression: str) -> Any:
    """AST 사전 검증된 수식을 sympy 객체로 변환한다.

    sympy.sympify 는 locals={} 로 호출하여 이름 해석 경로를 제거한다.
    rational=False 로 float 리터럴을 sympy.Float 로 보존한다.
    """
    sympy = _require_sympy()

    _validate_expression(expression)
    return sympy.sympify(expression, locals={}, rational=False)


def substitute(expr: Any, variables: dict[str, str]) -> Any:
    """sympy 식에 variables 를 치환한다. 값은 Decimal → sympy.Float 로 변환."""
    if not variables:
        return expr
    sympy = _require_sympy()
    subs_map: dict[Any, Any] = {}
    for name, raw in variables.items():
        sym = sympy.Symbol(name)
        # Decimal → 문자열 → sympy.Float 경유 (float 누수 차단).
        subs_map[sym] = sympy.Float(str(Decimal(raw)), _PRECISION)
    return expr.subs(subs_map)


def to_decimal_string(value: Any) -> str:
    """sympy 수치 또는 mpmath.mpf 를 Decimal 문자열로 직렬화한다.

    float 누수를 차단하기 위해 mpmath.nstr 경유 경로를 따른다.
    """
    sympy = _require_sympy()
    with mpmath.workdps(_PRECISION):
        numeric = value.evalf(_PRECISION) if hasattr(value, "evalf") else value
        if isinstance(numeric, sympy.Float):
            mpf = mpmath.mpf(str(numeric))
        elif isinstance(numeric, (int, sympy.Integer)):
            return str(Decimal(int(numeric)))
        elif isinstance(numeric, sympy.Rational):
            # 분수는 분자/분모 정수를 명시적으로 Decimal 나눗셈.
            num = Decimal(int(numeric.p))
            den = Decimal(int(numeric.q))
            return str(num / den)
        elif numeric.is_number is False or not numeric.is_real:
            # 실수가 아닌 (기호가 남은·복소) 값은 sympy 문자열로 반환.
            return str(numeric)
        else:
            mpf = mpmath.mpf(str(numeric))
        return str(mpmath_to_decimal(mpf, digits=_PRECISION))


def is_complex(value: Any) -> bool:
    """sympy 값이 실수가 아닌(순허수·복소·기호) 경우 True."""
    sympy = _require_sympy()
    if isinstance(value, (int, float)):
        return False
    if isinstance(value, sympy.Expr):
        try:
            return bool(value.is_real is False and value.is_complex)
        except Exception:
            return False
    return False
