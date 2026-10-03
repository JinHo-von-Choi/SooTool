"""core.calc 값 변환 보조 함수.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import mpmath

from sootool.core.cast import mpmath_to_decimal
from sootool.core.errors import (
    DomainConstraintError,
    UndefinedVariableError,
)


def _constant_value(name: str) -> Any:
    if name == "pi":
        return mpmath.mp.pi
    if name == "e":
        return mpmath.mp.e
    if name == "tau":
        return 2 * mpmath.mp.pi
    raise UndefinedVariableError(name)


def _variable_value(name: str, variables: dict[str, str]) -> Decimal:
    raw = variables.get(name)
    if raw is None:
        raise UndefinedVariableError(name)
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise DomainConstraintError(
            f"variable {name!r} is not a valid Decimal string: {raw!r}",
        ) from exc


def _literal_to_decimal(value: int | float) -> Decimal:
    if isinstance(value, float):
        # float 누수를 막기 위해 문자열 경유.
        return Decimal(repr(value))
    return Decimal(value)


def _is_integer_decimal(x: Decimal) -> bool:
    return x == x.to_integral_value()


def _to_mpf(x: Decimal | Any) -> Any:
    if isinstance(x, Decimal):
        return mpmath.mpf(str(x))
    return x


def _normalize_result(value: Any, precision: int) -> str:
    if isinstance(value, Decimal):
        return str(value)
    with mpmath.workdps(precision):
        return str(mpmath_to_decimal(value, digits=precision))
