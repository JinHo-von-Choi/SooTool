"""Crypto hash tools: SHA-256, SHA-512, BLAKE2b via stdlib hashlib."""
from __future__ import annotations

import hashlib
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_SUPPORTED_ALGORITHMS = frozenset({"sha256", "sha512", "blake2b"})


@REGISTRY.tool(
    namespace="crypto",
    name="hash",
    description="데이터 문자열의 해시를 반환합니다. algorithm: sha256 | sha512 | blake2b.",
    version="1.0.0",
)
def hash_data(data: str, algorithm: str = "sha256") -> dict[str, Any]:
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
