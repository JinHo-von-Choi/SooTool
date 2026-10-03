"""ed25519 서명 기반 함수 (정책 번들과 계산 영수증이 공유한다).

키와 서명은 base64 로 인코딩한 원시 바이트(개인 키 32바이트, 공개 키 32바이트, 서명 64바이트)다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sootool.core.errors import InvalidInputError

_KEY_ID_HEX_CHARS = 16


class SignatureVerificationError(Exception):
    """서명 검증 실패. 잘못된 형식의 키나 서명 입력도 이 오류로 반환한다."""


def load_private_key(private_key_b64: str) -> Ed25519PrivateKey:
    """base64 개인 키를 읽는다. 형식이 올바르지 않으면 InvalidInputError."""
    try:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64, validate=True))
    except ValueError as exc:
        raise InvalidInputError("private_key_b64 is not a valid base64 ed25519 private key") from exc


def key_id(private_key: Ed25519PrivateKey) -> str:
    """공개 키 SHA-256 앞부분. 서명 주체를 식별하는 용도다."""
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()[:_KEY_ID_HEX_CHARS]


def sign_with(private_key: Ed25519PrivateKey, payload: bytes) -> str:
    return base64.b64encode(private_key.sign(payload)).decode("ascii")


def sign_bytes(payload: bytes, private_key_b64: str) -> str:
    """payload 에 서명하고 base64 서명을 반환한다."""
    return sign_with(load_private_key(private_key_b64), payload)


def verify_bytes(payload: bytes, signature_b64: str, public_key_b64: str) -> None:
    """서명을 검증한다. 실패하면 형식 오류를 포함해 SignatureVerificationError 를 낸다."""
    try:
        key_bytes  = base64.b64decode(public_key_b64, validate=True)
        sig_bytes  = base64.b64decode(signature_b64, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(key_bytes)
    except ValueError as exc:
        raise SignatureVerificationError("Malformed public key or signature") from exc
    try:
        public_key.verify(sig_bytes, payload)
    except InvalidSignature as exc:
        raise SignatureVerificationError("Bundle signature is invalid") from exc
