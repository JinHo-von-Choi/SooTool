"""Advanced number theory: extended Euclidean, CRT, Euler's totient, Carmichael function.

내부 자료형 (ADR-008): 정수 연산 (Python int). 경계에서 str 직렬화.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import math
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"{name}은(는) 정수 문자열이어야 합니다: {value!r}") from exc


def _egcd(a: int, b: int) -> tuple[int, int, int]:
    """Iterative extended Euclidean algorithm.

    Returns (g, x, y) such that a*x + b*y = g = gcd(a, b).
    Works for any integers (positive, negative, zero).
    """
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


@REGISTRY.tool(
    namespace="crypto",
    name="egcd",
    description=(
        "확장 유클리드 알고리즘: gcd(a, b) = a*x + b*y. "
        "반환 {gcd, x, y} — Bezout 계수 (x, y)."
    ),
    version="1.0.0",
)
def egcd(a: str, b: str) -> dict[str, Any]:
    trace = CalcTrace(tool="crypto.egcd", formula="a*x + b*y = gcd(a, b)")
    ai = _parse_int(a, "a")
    bi = _parse_int(b, "b")
    trace.input("a", a)
    trace.input("b", b)

    g, x, y = _egcd(ai, bi)
    if g < 0:
        g, x, y = -g, -x, -y  # normalize gcd to non-negative

    trace.step("gcd", str(g))
    trace.step("x",   str(x))
    trace.step("y",   str(y))
    trace.output({"gcd": str(g), "x": str(x), "y": str(y)})

    return {"gcd": str(g), "x": str(x), "y": str(y), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="crypto",
    name="crt",
    description=(
        "중국인의 나머지 정리 (CRT): 연립합동식 x ≡ r_i (mod m_i) 해. "
        "moduli는 쌍별 서로소여야 함 (gcd=1). 반환 {x, modulus}."
    ),
    version="1.0.0",
)
def crt(residues: list[str], moduli: list[str]) -> dict[str, Any]:
    trace = CalcTrace(
        tool="crypto.crt",
        formula="x ≡ r_i (mod m_i), m_i 쌍별 서로소 가정",
    )
    if not isinstance(residues, list) or not residues:
        raise InvalidInputError("residues는 비어있지 않은 리스트여야 합니다.")
    if not isinstance(moduli, list) or not moduli:
        raise InvalidInputError("moduli는 비어있지 않은 리스트여야 합니다.")
    if len(residues) != len(moduli):
        raise InvalidInputError(
            f"residues({len(residues)}) 와 moduli({len(moduli)}) 길이가 같아야 합니다."
        )

    r_list = [_parse_int(r, f"residues[{i}]") for i, r in enumerate(residues)]
    m_list = [_parse_int(m, f"moduli[{i}]")   for i, m in enumerate(moduli)]

    for i, m in enumerate(m_list):
        if m <= 0:
            raise DomainConstraintError(f"moduli[{i}]={m} — 양의 정수여야 합니다.")

    # Pairwise coprimality
    for i in range(len(m_list)):
        for j in range(i + 1, len(m_list)):
            if math.gcd(m_list[i], m_list[j]) != 1:
                raise DomainConstraintError(
                    f"moduli[{i}]={m_list[i]} 와 moduli[{j}]={m_list[j]} 가 서로소가 아닙니다."
                )

    trace.input("residues", residues)
    trace.input("moduli",   moduli)

    # Iterative combination via Garner's algorithm / CRT direct
    M = 1
    for m in m_list:
        M *= m
    x = 0
    for r, m in zip(r_list, m_list, strict=True):
        M_i = M // m
        _, inv, _ = _egcd(M_i, m)
        x = (x + r * M_i * inv) % M
    x = x % M

    trace.step("x",       str(x))
    trace.step("modulus", str(M))
    trace.output({"x": str(x), "modulus": str(M)})

    return {"x": str(x), "modulus": str(M), "trace": trace.to_dict()}


def _factorize(n: int) -> dict[int, int]:
    """Trial-division factorization for n >= 2. Returns {prime: exponent}."""
    if n < 2:
        raise DomainConstraintError(f"n={n} — 2 이상의 정수가 필요합니다.")
    factors: dict[int, int] = {}
    # 2 separately
    while n % 2 == 0:
        factors[2] = factors.get(2, 0) + 1
        n //= 2
    p = 3
    while p * p <= n:
        while n % p == 0:
            factors[p] = factors.get(p, 0) + 1
            n //= p
        p += 2
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


_TRIAL_DIV_LIMIT = 10**14  # 방어적 상한: 너무 큰 수는 거부


@REGISTRY.tool(
    namespace="crypto",
    name="euler_totient",
    description=(
        "오일러 토션트 φ(n) = n * Π(1 - 1/p). n ≤ 10^14 (trial-division 한도). "
        "반환 {phi, factorization}."
    ),
    version="1.0.0",
)
def euler_totient(n: str) -> dict[str, Any]:
    trace = CalcTrace(
        tool="crypto.euler_totient",
        formula="φ(n) = n * Π_{p|n} (1 - 1/p)",
    )
    ni = _parse_int(n, "n")
    if ni < 1:
        raise DomainConstraintError(f"n은 양의 정수여야 합니다: {ni}")
    if ni > _TRIAL_DIV_LIMIT:
        raise DomainConstraintError(
            f"n={ni} 는 trial-division 한도 {_TRIAL_DIV_LIMIT} 를 초과합니다."
        )

    trace.input("n", n)
    if ni == 1:
        trace.step("phi", "1")
        trace.output({"phi": "1", "factorization": {}})
        return {"phi": "1", "factorization": {}, "trace": trace.to_dict()}

    factors = _factorize(ni)
    phi = ni
    for p in factors:
        phi = phi // p * (p - 1)

    fact_serialized = {str(p): e for p, e in factors.items()}
    trace.step("factorization", fact_serialized)
    trace.step("phi",           str(phi))
    trace.output({"phi": str(phi), "factorization": fact_serialized})

    return {
        "phi":           str(phi),
        "factorization": fact_serialized,
        "trace":         trace.to_dict(),
    }


def _carmichael_from_factors(factors: dict[int, int]) -> int:
    """Compute λ(n) using the factorization."""
    lambdas: list[int] = []
    for p, e in factors.items():
        if p == 2:
            if e == 1:
                lambdas.append(1)
            elif e == 2:
                lambdas.append(2)
            else:
                lambdas.append(2 ** (e - 2))
        else:
            lambdas.append((p - 1) * p ** (e - 1))
    result = 1
    for x in lambdas:
        result = math.lcm(result, x)
    return result


@REGISTRY.tool(
    namespace="crypto",
    name="carmichael_lambda",
    description=(
        "카마이클 함수 λ(n) = lcm(λ(p^k) for prime powers). n ≤ 10^14."
    ),
    version="1.0.0",
)
def carmichael_lambda(n: str) -> dict[str, Any]:
    trace = CalcTrace(
        tool="crypto.carmichael_lambda",
        formula="λ(n) = lcm_{p^k || n} λ(p^k)",
    )
    ni = _parse_int(n, "n")
    if ni < 1:
        raise DomainConstraintError(f"n은 양의 정수여야 합니다: {ni}")
    if ni > _TRIAL_DIV_LIMIT:
        raise DomainConstraintError(
            f"n={ni} 는 trial-division 한도 {_TRIAL_DIV_LIMIT} 를 초과합니다."
        )

    trace.input("n", n)
    if ni == 1:
        trace.step("lambda", "1")
        trace.output({"lambda": "1", "factorization": {}})
        return {"lambda": "1", "factorization": {}, "trace": trace.to_dict()}

    factors = _factorize(ni)
    lam     = _carmichael_from_factors(factors)
    fact_serialized = {str(p): e for p, e in factors.items()}

    trace.step("factorization", fact_serialized)
    trace.step("lambda",        str(lam))
    trace.output({"lambda": str(lam), "factorization": fact_serialized})

    return {
        "lambda":        str(lam),
        "factorization": fact_serialized,
        "trace":         trace.to_dict(),
    }
