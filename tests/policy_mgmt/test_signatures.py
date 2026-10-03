from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sootool.core.errors import InvalidInputError
from sootool.policy_mgmt.signatures import (
    SignatureVerificationError,
    bundle_payload_bytes,
    sign_bundle,
    verify_bundle,
)


def _keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    private_b64 = base64.b64encode(
        private.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
    ).decode("ascii")
    public_b64 = base64.b64encode(
        private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    return private_b64, public_b64


def test_sign_then_verify_roundtrip():
    private_b64, public_b64 = _keypair()
    payload   = bundle_payload_bytes("rate: 0.1\n", {"domain": "tax", "year": 2026})
    signature = sign_bundle(payload, private_b64)
    verify_bundle(payload, signature, public_b64)


def test_tampered_payload_fails_verification():
    private_b64, public_b64 = _keypair()
    signature = sign_bundle(bundle_payload_bytes("rate: 0.1\n", {"year": 2026}), private_b64)
    tampered  = bundle_payload_bytes("rate: 0.2\n", {"year": 2026})
    with pytest.raises(SignatureVerificationError):
        verify_bundle(tampered, signature, public_b64)


def test_tampered_metadata_fails_verification():
    private_b64, public_b64 = _keypair()
    signature = sign_bundle(bundle_payload_bytes("rate: 0.1\n", {"year": 2026}), private_b64)
    tampered  = bundle_payload_bytes("rate: 0.1\n", {"year": 2027})
    with pytest.raises(SignatureVerificationError):
        verify_bundle(tampered, signature, public_b64)


def test_signature_from_other_key_fails_verification():
    private_b64, _ = _keypair()
    _, other_public = _keypair()
    payload   = bundle_payload_bytes("a: 1\n", {})
    signature = sign_bundle(payload, private_b64)
    with pytest.raises(SignatureVerificationError):
        verify_bundle(payload, signature, other_public)


@pytest.mark.parametrize(
    ("signature", "public_key"),
    [
        ("not base64 !!", "AAAA"),
        ("AAAA", "not base64 !!"),
        ("AAAA", "AAAA"),
        ("", ""),
    ],
)
def test_malformed_inputs_fail_closed_with_typed_error(signature, public_key):
    with pytest.raises(SignatureVerificationError):
        verify_bundle(b"payload", signature, public_key)


@pytest.mark.parametrize("private_key", ["not base64 !!", "AAAA", ""])
def test_sign_rejects_malformed_private_key(private_key):
    with pytest.raises(InvalidInputError):
        sign_bundle(b"payload", private_key)


def test_payload_is_independent_of_metadata_key_order():
    first  = bundle_payload_bytes("a: 1\n", {"domain": "tax", "year": 2026})
    second = bundle_payload_bytes("a: 1\n", {"year": 2026, "domain": "tax"})
    assert first == second


def test_payload_changes_with_yaml_content():
    assert bundle_payload_bytes("a: 1\n", {}) != bundle_payload_bytes("a: 2\n", {})


# --- policy_export / policy_import 연동 ---

def _admin_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))


def _signed_bundle(private_b64: str) -> dict:
    import os
    import tempfile

    from sootool.policy_mgmt.tools import policy_export

    fd, key_path = tempfile.mkstemp(prefix="sootool-test-key-")
    try:
        with os.fdopen(fd, "w", encoding="ascii") as handle:
            handle.write(private_b64)
        previous = os.environ.get("SOOTOOL_POLICY_KEY_FILE")
        os.environ["SOOTOOL_POLICY_KEY_FILE"] = key_path
        try:
            return policy_export(domain="tax", name="kr_income", year=2026, include_signature=True)["bundle"]
        finally:
            if previous is None:
                os.environ.pop("SOOTOOL_POLICY_KEY_FILE", None)
            else:
                os.environ["SOOTOOL_POLICY_KEY_FILE"] = previous
    finally:
        os.unlink(key_path)


def test_import_accepts_correctly_signed_bundle(tmp_path, monkeypatch):
    from sootool.policy_mgmt.tools import policy_import

    _admin_env(tmp_path, monkeypatch)
    private_b64, public_b64 = _keypair()
    result = policy_import(
        _signed_bundle(private_b64), require_signature=True, public_key_b64=public_b64,
    )
    assert "error" not in result, result


def test_import_rejects_bundle_signed_by_other_key(tmp_path, monkeypatch):
    from sootool.policy_mgmt.tools import policy_import

    _admin_env(tmp_path, monkeypatch)
    private_b64, _ = _keypair()
    _, other_public = _keypair()
    result = policy_import(
        _signed_bundle(private_b64), require_signature=True, public_key_b64=other_public,
    )
    assert result["error"] == "signature_invalid"


def test_import_reports_malformed_public_key_as_signature_invalid(tmp_path, monkeypatch):
    from sootool.policy_mgmt.tools import policy_import

    _admin_env(tmp_path, monkeypatch)
    private_b64, _ = _keypair()
    result = policy_import(
        _signed_bundle(private_b64), require_signature=True, public_key_b64="not base64 !!",
    )
    assert result["error"] == "signature_invalid"


def test_import_requires_signature_when_environment_demands_it(tmp_path, monkeypatch):
    from sootool.policy_mgmt.tools import policy_export, policy_import

    _admin_env(tmp_path, monkeypatch)
    monkeypatch.setenv("SOOTOOL_POLICY_REQUIRE_SIGNATURE", "1")
    unsigned = policy_export(domain="tax", name="kr_income", year=2026)["bundle"]
    result   = policy_import(unsigned)
    assert result["error"] == "signature_required"


def test_export_requires_a_configured_key_file_when_signing(monkeypatch):
    from sootool.policy_mgmt.tools import policy_export

    monkeypatch.delenv("SOOTOOL_POLICY_KEY_FILE", raising=False)
    with pytest.raises(InvalidInputError):
        policy_export(domain="tax", name="kr_income", year=2026, include_signature=True)


def test_export_rejects_a_key_file_readable_by_others(tmp_path, monkeypatch):
    import os

    from sootool.policy_mgmt.tools import policy_export

    private_b64, _ = _keypair()
    key_file = tmp_path / "policy.key"
    key_file.write_text(private_b64, encoding="ascii")
    os.chmod(key_file, 0o644)
    monkeypatch.setenv("SOOTOOL_POLICY_KEY_FILE", str(key_file))
    with pytest.raises(InvalidInputError):
        policy_export(domain="tax", name="kr_income", year=2026, include_signature=True)


def test_export_does_not_accept_a_key_argument():
    import inspect

    from sootool.policy_mgmt.tools import policy_export

    assert "private_key_b64" not in inspect.signature(policy_export).parameters
