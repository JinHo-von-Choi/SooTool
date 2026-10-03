"""Shared helpers for the probability distribution tools.
"""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.lazy import lazy_module

stats = lazy_module("scipy.stats")


_SIG_DIGITS = 10  # significant digits for output


def _parse_float(value: str, name: str) -> float:
    try:
        return decimal_to_float64(D(value))
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


def _parse_prob(value: str, name: str) -> float:
    p = _parse_float(value, name)
    if p < 0.0 or p > 1.0:
        raise DomainConstraintError(f"{name}={value}은(는) [0, 1] 범위를 벗어납니다.")
    return p


def _parse_quantile(value: str, name: str) -> float:
    q = _parse_float(value, name)
    if q <= 0.0 or q >= 1.0:
        raise DomainConstraintError(f"{name}={value}은(는) (0, 1) 열린 구간이어야 합니다.")
    return q


def _validate_non_negative_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f"{name}은(는) 정수여야 합니다: {value!r}")
    if value < 0:
        raise DomainConstraintError(f"{name}은(는) 음수가 될 수 없습니다: {value}")


def _validate_positive_float(value: float, name: str, raw: str) -> None:
    if value <= 0.0:
        raise DomainConstraintError(f"{name}은(는) 양수여야 합니다: {raw}")


def _validate_nonneg_float(value: float, name: str, raw: str) -> None:
    if value < 0.0:
        raise DomainConstraintError(f"{name}은(는) 음수가 될 수 없습니다: {raw}")


def _dist_result(
    tool_name: str,
    formula: str,
    label: str,
    inputs: dict[str, Any],
    value: float,
) -> dict[str, Any]:
    trace = CalcTrace(tool=tool_name, formula=formula)
    for k_, v_ in inputs.items():
        trace.input(k_, v_)
    result_str = float64_to_decimal_str(value, digits=_SIG_DIGITS)
    trace.step(label, result_str)
    trace.output({"result": result_str})
    return {"result": result_str, "trace": trace.to_dict()}
