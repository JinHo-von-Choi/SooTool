"""ed25519 signature interface for policy bundles.

Key distribution UX is not yet implemented. This module exposes the
signing and verification interface only; actual key management is deferred.
The primitives are shared with sootool.core.signing.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sootool.core.signing import SignatureVerificationError, sign_bytes, verify_bytes

__all__ = [
    "SignatureVerificationError",
    "bundle_payload_bytes",
    "sign_bundle",
    "verify_bundle",
]

sign_bundle   = sign_bytes
verify_bundle = verify_bytes


def bundle_payload_bytes(yaml_content: str, metadata: dict[str, Any]) -> bytes:
    """Produce the canonical payload bytes for signing: sha256(yaml) + sorted metadata."""
    yaml_hash = hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()
    meta_str  = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
    return (yaml_hash + "\n" + meta_str).encode("utf-8")
