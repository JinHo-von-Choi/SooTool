"""Crypto hash tools: SHA-256, SHA-512, BLAKE2b via stdlib hashlib."""
from __future__ import annotations

import hashlib

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_SUPPORTED_ALGORITHMS = frozenset({"sha256", "sha512", "blake2b"})


class HashDataResult(TracedResult):
    hex: str


@REGISTRY.tool(
    namespace="crypto",
    name="hash",
    description=(
        "문자열을 UTF-8 로 인코딩해 해시를 소문자 16진수 hex 로 반환한다. "
        "algorithm 은 sha256(기본) | sha512 | blake2b(64바이트 출력)이며 대소문자를 구분하지 않는다. "
        "무결성 지문 확인용이고, 솔트와 반복이 없어 비밀번호 저장에는 쓰지 않는다."
    ),
    version="1.0.0",
)
def hash_data(data: str, algorithm: str = "sha256") -> HashDataResult:
    """Compute a cryptographic hash of a UTF-8 string.

    Args:
        data:      Input string (UTF-8).
        algorithm: Hash algorithm — "sha256", "sha512", or "blake2b".

    Returns:
        {hex, trace}
    """
    trace = CalcTrace(
        tool="crypto.hash",
        formula=f"{algorithm}(data)",
    )
    trace.input("data",      data)
    trace.input("algorithm", algorithm)

    algo = algorithm.lower()
    if algo not in _SUPPORTED_ALGORITHMS:
        raise InvalidInputError(
            f"지원하지 않는 알고리즘: {algorithm!r}. "
            f"지원 알고리즘: {sorted(_SUPPORTED_ALGORITHMS)}"
        )

    encoded = data.encode("utf-8")

    if algo == "sha256":
        digest = hashlib.sha256(encoded).hexdigest()
    elif algo == "sha512":
        digest = hashlib.sha512(encoded).hexdigest()
    else:
        digest = hashlib.blake2b(encoded).hexdigest()

    trace.step("hex_length", str(len(digest)))
    trace.output({"hex": digest})

    return {"hex": digest, "trace": trace.to_dict()}
