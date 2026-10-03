"""crypto 도구가 공유하는 정수 문자열 파서."""
from __future__ import annotations

from sootool.core.errors import InvalidInputError
from sootool.core.limits import ensure_max


def parse_int(value: str, name: str) -> int:
    """정수 문자열을 읽는다. 자릿수가 CRYPTO_DIGITS 한도를 넘으면 InputLimitError."""
    if isinstance(value, str):
        ensure_max("CRYPTO_DIGITS", len(value.lstrip("+-")), name)
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"{name}은(는) 정수 문자열이어야 합니다: {value!r}") from exc
