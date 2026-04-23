"""Polynomial tools: numerical root finding and Horner evaluation.

내부 자료형 (ADR-008):
- 계수 입력은 Decimal 문자열 리스트. 호너 평가는 Decimal 연산.
- 근 찾기는 numpy.roots (복소수 float64), 결과는 {real, imag} Decimal 문자열 쌍.

입력 관례:
- coefficients 는 높은 차수부터 내림차순. 예: [1, 0, -4] → x² - 4.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from typing import Any

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_SIG = 12


def _parse_coefs(coefs: list[str]) -> list[Any]:
    if not isinstance(coefs, list) or not coefs:
        raise InvalidInputError("coefficients는 비어있지 않은 리스트여야 합니다.")
    try:
        return [D(c) for c in coefs]
    except Exception as exc:
        raise InvalidInputError("coefficients 요소는 Decimal 문자열이어야 합니다.") from exc


@REGISTRY.tool(
    namespace="math",
    name="polynomial_roots",
    description=(
        "다항식의 수치 근을 반환한다. coefficients는 높은 차수 → 낮은 차수 순 Decimal 문자열 리스트. "
        "numpy.roots 사용. 각 근은 {real, imag} Decimal 문자열 쌍."
    ),
    version="1.0.0",
)
def polynomial_roots(coefficients: list[str]) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.polynomial_roots",
        formula="P(x) = Σ a_i x^(n-i) = 0, numpy.roots 기반 고유값 분해",
    )
    coefs_dec = _parse_coefs(coefficients)
    if len(coefs_dec) < 2:
        raise InvalidInputError("근을 찾으려면 최소 degree=1 (계수 2개) 이상이어야 합니다.")
    if coefs_dec[0] == D("0"):
        raise InvalidInputError("최고 차수 계수는 0이 될 수 없습니다.")

    coefs_f = np.array([decimal_to_float64(c) for c in coefs_dec], dtype=np.float64)
    trace.input("coefficients", coefficients)

    roots = np.roots(coefs_f)
    roots_list: list[dict[str, str]] = []
    for r in roots:
        re = float(r.real)
        im = float(r.imag)
        roots_list.append({
            "real": float64_to_decimal_str(re, digits=_SIG),
            "imag": float64_to_decimal_str(im, digits=_SIG),
        })

    trace.step("roots_count", len(roots_list))
    trace.output({"roots_count": len(roots_list)})

    return {
        "roots":  roots_list,
        "degree": len(coefs_dec) - 1,
        "trace":  trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="math",
    name="polynomial_horner",
    description=(
        "호너 방법으로 다항식 P(x) 값을 Decimal 정밀로 평가. "
        "coefficients는 높은 차수 → 낮은 차수 순."
    ),
    version="1.0.0",
)
def polynomial_horner(coefficients: list[str], x: str) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.polynomial_horner",
        formula="P(x) = (...((a_0 x + a_1) x + a_2) x + ... + a_n)",
    )
    coefs_dec = _parse_coefs(coefficients)
    try:
        x_dec = D(x)
    except Exception as exc:
        raise InvalidInputError(f"x는 Decimal 문자열이어야 합니다: {x!r}") from exc

    trace.input("coefficients", coefficients)
    trace.input("x", x)

    acc = D("0")
    for c in coefs_dec:
        acc = acc * x_dec + c
    result_str = str(acc)
    trace.step("P(x)", result_str)
    trace.output({"result": result_str})

    return {
        "result": result_str,
        "degree": len(coefs_dec) - 1,
        "trace":  trace.to_dict(),
    }
