"""Crypto arithmetic tools: GCD, LCM, modular exponentiation, modular inverse."""
from __future__ import annotations

import math

from sootool.core.audit import CalcTrace
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.crypto._ints import parse_int

_parse_int = parse_int


class GcdResult(TracedResult):
    result: str


class LcmResult(TracedResult):
    result: str


class ModpowResult(TracedResult):
    result: str


class ModinvResult(TracedResult):
    result: str


@REGISTRY.tool(
    namespace="crypto",
    name="gcd",
    description=(
        "두 정수의 최대공약수(GCD)를 구한다. a, b 는 정수 문자열(부호는 무시, 자릿수 한도 2048)이고 "
        "결과 result 는 정수 문자열이다. 둘 다 0 이면 0. 소수점이나 쉼표가 든 값은 거부하며, "
        "세 수 이상은 결과를 다시 넣어 이어서 호출한다."
    ),
    version="1.0.0",
)
def gcd(a: str, b: str) -> GcdResult:
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
    description=(
        "두 정수의 최소공배수(LCM)를 구한다. a, b 는 정수 문자열(부호는 무시, 자릿수 한도 2048)이고 "
        "큰 정수도 정확히 계산해 result 를 정수 문자열로 돌려준다. 둘 중 하나가 0 이면 0 이다. "
        "분수의 통분에는 분모들의 LCM 을 쓰되, 소수 입력은 받지 않는다."
    ),
    version="1.0.0",
)
def lcm(a: str, b: str) -> LcmResult:
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
    description=(
        "모듈러 거듭제곱 base^exponent mod modulus 를 구한다. 세 인자는 정수 문자열(자릿수 한도 2048)이며 "
        "modulus 는 1 이상, exponent 는 0 이상이어야 한다. result 는 0 이상 modulus 미만의 정수 문자열이다. "
        "음수 지수로 역원을 구하려면 modinv 를 쓴다."
    ),
    version="1.0.0",
)
def modpow(base: str, exponent: str, modulus: str) -> ModpowResult:
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
    description=(
        "모듈러 역원 a^-1 mod m 을 구한다. a, m 은 정수 문자열(자릿수 한도 2048)이고 m 은 2 이상이어야 한다. "
        "result 는 0 이상 m 미만이며, gcd(a, m) 이 1 이 아니면 역원이 없어 오류가 난다. "
        "a 가 0 이거나 m 과 약수를 공유하면 역원이 없다."
    ),
    version="1.0.0",
)
def modinv(a: str, m: str) -> ModinvResult:
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
