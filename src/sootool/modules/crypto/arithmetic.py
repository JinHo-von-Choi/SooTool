"""Crypto arithmetic tools: GCD, LCM, modular exponentiation, modular inverse."""
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
        raise InvalidInputError(f"{name} 은(는) 정수 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="crypto",
    name="gcd",
    description="두 정수의 최대공약수(GCD)를 반환합니다. 유클리드 호제법 사용.",
    version="1.0.0",
)
def gcd(a: str, b: str) -> dict[str, Any]:
    """Compute greatest common divisor of two integers.

    Args:
        a: First integer as string.
        b: Second integer as string.

    Returns:
        {result, trace}
    """
    trace = CalcTrace(tool="crypto.gcd", formula="gcd(a, b)")
    trace.input("a", a)
    trace.input("b", b)

    ai = abs(_parse_int(a, "a"))
    bi = abs(_parse_int(b, "b"))

    result = math.gcd(ai, bi)

    trace.step("gcd", str(result))
    trace.output({"result": str(result)})

    return {"result": str(result), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="crypto",
    name="lcm",
    description="두 정수의 최소공배수(LCM)를 반환합니다.",
    version="1.0.0",
)
def lcm(a: str, b: str) -> dict[str, Any]:
    """Compute least common multiple of two integers.

    Args:
        a: First integer as string.
        b: Second integer as string.

    Returns:
        {result, trace}
    """
    trace = CalcTrace(tool="crypto.lcm", formula="lcm(a, b) = a*b / gcd(a,b)")
    trace.input("a", a)
    trace.input("b", b)

    ai = abs(_parse_int(a, "a"))
    bi = abs(_parse_int(b, "b"))

    result = math.lcm(ai, bi)

    trace.step("lcm", str(result))
    trace.output({"result": str(result)})

    return {"result": str(result), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="crypto",
    name="modpow",
    description="모듈러 거듭제곱: base^exponent mod modulus. Python 내장 pow(b,e,m) 사용.",
    version="1.0.0",
)
def modpow(base: str, exponent: str, modulus: str) -> dict[str, Any]:
    """Compute modular exponentiation: base ** exponent % modulus.

    Args:
        base:     Base integer as string.
        exponent: Exponent integer as string (non-negative).
        modulus:  Modulus integer as string (> 0).

    Returns:
        {result, trace}
    """
    trace = CalcTrace(
        tool="crypto.modpow",
        formula="pow(base, exponent, modulus)",
    )
    trace.input("base",     base)
    trace.input("exponent", exponent)
    trace.input("modulus",  modulus)

    b = _parse_int(base,     "base")
    e = _parse_int(exponent, "exponent")
    m = _parse_int(modulus,  "modulus")

    if m <= 0:
        raise DomainConstraintError(f"modulus 는 양의 정수여야 합니다: {m}")
    if e < 0:
        raise DomainConstraintError(f"exponent 는 음수가 될 수 없습니다: {e}")

    result = pow(b, e, m)

    trace.step("result", str(result))
    trace.output({"result": str(result)})

    return {"result": str(result), "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="crypto",
    name="modinv",
    description="모듈러 역원: a^-1 mod m. gcd(a,m) != 1 이면 DomainConstraintError 발생.",
    version="1.0.0",
)
def modinv(a: str, m: str) -> dict[str, Any]:
    """Compute modular multiplicative inverse of a modulo m.

    Uses Python 3.8+ built-in pow(a, -1, m).
    Raises DomainConstraintError if gcd(a, m) != 1 (inverse does not exist).

    Args:
        a: Integer as string.
        m: Modulus as string (> 1).

    Returns:
        {result, trace}
    """
    trace = CalcTrace(
        tool="crypto.modinv",
        formula="pow(a, -1, m)",
    )
    trace.input("a", a)
    trace.input("m", m)

    ai = _parse_int(a, "a")
    mi = _parse_int(m, "m")

    if mi <= 1:
        raise DomainConstraintError(f"m 은 1 보다 커야 합니다: {mi}")

    g = math.gcd(abs(ai), abs(mi))
    if g != 1:
        raise DomainConstraintError(
            f"gcd({ai}, {mi}) = {g} != 1 이므로 모듈러 역원이 존재하지 않습니다."
        )

    result = pow(ai, -1, mi)

    trace.step("gcd", str(g))
    trace.step("result", str(result))
    trace.output({"result": str(result)})

    return {"result": str(result), "trace": trace.to_dict()}
