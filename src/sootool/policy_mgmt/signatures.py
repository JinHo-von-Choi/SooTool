"""ed25519 signature interface for policy bundles.

Key distribution UX is not yet implemented. This module exposes the
signing and verification interface only; actual key management is deferred.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sootool.core.errors import InvalidInputError


class SignatureVerificationError(Exception):
    """Raised when a bundle signature fails verification."""


def sign_bundle(payload_bytes: bytes, private_key_b64: str) -> str:
    """Sign a bundle payload using an ed25519 private key (base64-encoded).

    Returns a base64-encoded signature string.
    """
    try:
        key_bytes   = base64.b64decode(private_key_b64, validate=True)
        private_key = Ed25519PrivateKey.from_private_bytes(key_bytes)
    except ValueError as exc:
        raise InvalidInputError("private_key_b64 is not a valid base64 ed25519 private key") from exc
    sig = private_key.sign(payload_bytes)
    return base64.b64encode(sig).decode("ascii")


def verify_bundle(payload_bytes: bytes, signature_b64: str, public_key_b64: str) -> None:
    """Verify an ed25519 bundle signature.

    Raises SignatureVerificationError on any failure, including malformed key or signature input.
    """
    try:
        key_bytes  = base64.b64decode(public_key_b64, validate=True)
        sig_bytes  = base64.b64decode(signature_b64, validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(key_bytes)
    except ValueError as exc:
        raise SignatureVerificationError("Malformed public key or signature") from exc
    try:
        public_key.verify(sig_bytes, payload_bytes)
    except InvalidSignature as exc:
        raise SignatureVerificationError("Bundle signature is invalid") from exc


def bundle_payload_bytes(yaml_content: str, metadata: dict[str, Any]) -> bytes:
    """Produce the canonical payload bytes for signing: sha256(yaml) + sorted metadata."""
    yaml_hash = hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()
    meta_str  = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    return (yaml_hash + "\n" + meta_str).encode("utf-8")
