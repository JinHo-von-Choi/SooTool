"""Crypto primality testing: Miller-Rabin probabilistic primality test."""
from __future__ import annotations

import random
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def _miller_rabin_witness(n: int, a: int) -> bool:
    """Return True if `a` is a witness to n being composite.

    Performs a single round of the Miller-Rabin test with witness `a`.
    """
    # Write n-1 as 2^r * d where d is odd
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    x = pow(a, d, n)
    if x == 1 or x == n - 1:
        return False  # inconclusive — not a witness

    for _ in range(r - 1):
        x = pow(x, 2, n)
        if x == n - 1:
            return False  # inconclusive

    return True  # a is a witness → n is composite


def _is_prime_miller_rabin(n: int, k: int = 20) -> bool:
    """Deterministic for small n, probabilistic Miller-Rabin for larger n.

    Uses fixed witness sets for n < 3,215,031,751 and n < 3,317,044,064,679,887,385,961,981
    to guarantee correctness, then falls back to k random witnesses.
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False

    # For small n, use deterministic sets of witnesses
    # Source: https://en.wikipedia.org/wiki/Miller%E2%80%93Rabin_primality_test#Testing_against_small_sets_of_bases
    if n < 2_047:
        witnesses = [2]
    elif n < 1_373_653:
        witnesses = [2, 3]
    elif n < 9_080_191:
        witnesses = [31, 73]
    elif n < 25_326_001:
        witnesses = [2, 3, 5]
    elif n < 3_215_031_751:
        witnesses = [2, 3, 5, 7]
    elif n < 4_759_123_141:
        witnesses = [2, 7, 61]
    elif n < 1_122_004_669_633:
        witnesses = [2, 13, 23, 1_662_803]
    elif n < 2_152_302_898_747:
        witnesses = [2, 3, 5, 7, 11]
    elif n < 3_474_749_660_383:
        witnesses = [2, 3, 5, 7, 11, 13]
    elif n < 341_550_071_728_321:
        witnesses = [2, 3, 5, 7, 11, 13, 17]
    elif n < 3_825_123_056_546_413_051:
        witnesses = [2, 3, 5, 7, 11, 13, 17, 19, 23]
    else:
        # For very large n, use k random witnesses
        witnesses = [random.randrange(2, min(n - 1, 10**9)) for _ in range(k)]

    for a in witnesses:
        a_mod = a % n
        if a_mod < 2:
            continue
        if _miller_rabin_witness(n, a_mod):
            return False

    return True


@REGISTRY.tool(
    namespace="crypto",
    name="is_prime",
    description="Miller-Rabin 소수 판별. n: 정수 문자열, k: 라운드 수(기본 20).",
    version="1.0.0",
)
def is_prime(n: str, k: int = 20) -> dict[str, Any]:
    """Test whether n is (probably) prime using Miller-Rabin.

    For n below ~3.8 * 10^18, uses deterministic fixed witness sets,
    guaranteeing correctness. For larger n, uses k random rounds.

    Args:
        n: Integer to test as string.
        k: Number of Miller-Rabin rounds for very large n (default 20).

    Returns:
        {is_prime: bool, trace}
    """
    trace = CalcTrace(
        tool="crypto.is_prime",
        formula="Miller-Rabin(n, k)",
    )
    trace.input("n", n)
    trace.input("k", k)

    try:
        ni = int(n)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"n 은 정수 문자열이어야 합니다: {n!r}") from exc

    if k < 1:
        raise InvalidInputError(f"k 는 1 이상이어야 합니다: {k}")

    result = _is_prime_miller_rabin(ni, k)

    trace.step("result", str(result))
    trace.output({"is_prime": result})

    return {"is_prime": result, "trace": trace.to_dict()}
