"""계산 영수증: 선택적 서명과 서명 검증.

영수증은 응답의 ``_meta.integrity`` 블록이다. 환경변수 ``SOOTOOL_RECEIPT_KEY_FILE`` 에
base64 ed25519 개인 키 파일 경로가 지정되면 스탬프에 ``key_id`` 와 ``signature`` 를 더한다.
키는 파일 경로로만 참조하며 도구 인자로 받지 않는다. 서명 대상은 ``signature`` 를 제외한
스탬프의 정규화 JSON 이다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sootool.core.errors import InvalidInputError
from sootool.core.signing import (
    SignatureVerificationError,
    key_id,
    load_private_key,
    sign_with,
    verify_bytes,
)

log = logging.getLogger("sootool.core.receipts")

SIGNING_KEY_ENV: Final = "SOOTOOL_RECEIPT_KEY_FILE"

# 실행마다 달라지는 값(소요 시간, 실행 id)이 결과에 포함되어 재실행 검증이 성립하지 않는 도구.
NON_REPLAYABLE_TOOLS: Final = frozenset({
    "core.batch",
    "core.pipeline",
    "core.pipeline_resume",
    "sootool.verify_receipt",
})

# 재실행 결과와 영수증을 대조하는 필드. policy_sha256 은 양쪽 중 한쪽에만 있어도 불일치로 본다.
COMPARED_FIELDS: Final = ("tool", "input_hash", "result_hash", "tool_version", "policy_sha256")
REQUIRED_FIELDS: Final = ("tool", "input_hash", "result_hash", "tool_version")


@dataclass(frozen=True)
class _LoadedKey:
    key:    Ed25519PrivateKey
    key_id: str


_CACHE: dict[str, tuple[int, _LoadedKey | str]] = {}


def _load_key(path: str) -> _LoadedKey | str:
    """키 파일을 읽어 캐시한다. 실패하면 오류 코드 문자열을 반환한다."""
    try:
        mtime = Path(path).stat().st_mtime_ns
    except OSError:
        return "key_file_unreadable"
    cached = _CACHE.get(path)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        key    = load_private_key(Path(path).read_text(encoding="ascii").strip())
        loaded: _LoadedKey | str = _LoadedKey(key=key, key_id=key_id(key))
    except (OSError, UnicodeDecodeError):
        loaded = "key_file_unreadable"
    except InvalidInputError:
        loaded = "key_malformed"
    _CACHE[path] = (mtime, loaded)
    return loaded


def signing_payload(stamp: dict[str, Any]) -> bytes:
    """서명 대상 바이트: signature 를 제외한 스탬프의 정규화 JSON."""
    body = {k: v for k, v in stamp.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign_stamp(stamp: dict[str, Any]) -> dict[str, Any]:
    """키 파일이 설정돼 있으면 스탬프에 key_id 와 signature 를 더한 사본을 반환한다.

    키 설정이 있는데 읽을 수 없으면 서명 없이 ``signature_error`` 코드를 남긴다. 계산 결과는
    서명 실패와 무관하게 반환된다.
    """
    path = os.environ.get(SIGNING_KEY_ENV, "").strip()
    if not path:
        return stamp
    loaded = _load_key(path)
    if isinstance(loaded, str):
        log.warning("receipt signing skipped: %s", loaded)
        return {**stamp, "signature_error": loaded}
    signed = {**stamp, "key_id": loaded.key_id}
    signed["signature"] = sign_with(loaded.key, signing_payload(signed))
    return signed


def verify_stamp_signature(stamp: dict[str, Any], public_key_b64: str) -> None:
    """스탬프 서명을 공개 키로 검증한다. 실패하면 SignatureVerificationError."""
    signature = stamp.get("signature")
    if not isinstance(signature, str):
        raise SignatureVerificationError("Receipt has no signature")
    verify_bytes(signing_payload(stamp), signature, public_key_b64)
