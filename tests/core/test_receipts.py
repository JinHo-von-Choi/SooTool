from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sootool import server
from sootool.core.audit import integrity_stamp, result_hash
from sootool.core.errors import InvalidInputError
from sootool.core.receipts import SIGNING_KEY_ENV, sign_stamp
from sootool.core.registry import REGISTRY

_LOAN = {"principal": "1000000", "annual_rate": "0.05", "months": 12}


@pytest.fixture(autouse=True)
def _loaded(monkeypatch) -> None:
    server._load_modules()
    monkeypatch.delenv(SIGNING_KEY_ENV, raising=False)


def _receipt(tool: str = "finance.loan_schedule", **kwargs: Any) -> dict[str, Any]:
    return REGISTRY.invoke(tool, **(kwargs or _LOAN))["_meta"]["integrity"]


def _keypair(tmp_path: Path) -> tuple[Path, str]:
    private = Ed25519PrivateKey.generate()
    private_b64 = base64.b64encode(
        private.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption(),
        )
    ).decode("ascii")
    public_b64 = base64.b64encode(
        private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode("ascii")
    key_file = tmp_path / "receipt.key"
    key_file.write_text(private_b64, encoding="ascii")
    return key_file, public_b64


# --- 스탬프 구성 ---

def test_stamp_carries_tool_and_result_hash():
    stamp = _receipt()
    assert stamp["tool"] == "finance.loan_schedule"
    assert len(stamp["result_hash"]) == 64


def test_result_hash_ignores_meta_at_every_level():
    body = {"result": "1", "trace": {"output": "1"}, "nested": [{"_meta": {"x": 1}, "v": 2}]}
    with_meta = {**body, "_meta": {"hints": [1], "session_stats": {"tool_calls": 9}}}
    with_meta["nested"] = [{"_meta": {"x": 99}, "v": 2}]
    assert result_hash(body) == result_hash(with_meta)


def test_result_hash_changes_with_result_content():
    assert result_hash({"result": "1"}) != result_hash({"result": "2"})


def test_result_hash_is_deterministic_across_calls():
    assert _receipt()["result_hash"] == _receipt()["result_hash"]


@pytest.mark.parametrize(
    ("tool", "kwargs"),
    [
        ("core.add", {"operands": ["0.1", "0.2"]}),
        ("core.calc", {"expression": "sqrt(2)*3"}),
        ("tax.progressive", {
            "taxable_income": "50000000",
            "brackets": [{"upper": "14000000", "rate": "0.06"}, {"upper": None, "rate": "0.15"}],
        }),
        ("datetime.age", {"birth_date": "1990-06-15", "reference_date": "2026-04-22"}),
        ("stats.ci_mean", {"values": ["1", "2", "3", "4", "5"]}),
        ("pm.monte_carlo_schedule", {
            "tasks": [{"id": "a", "optimistic": "1", "most_likely": "2", "pessimistic": "3"}],
            "n": 200,
        }),
    ],
)
def test_result_hash_is_stable_for_representative_tools(tool, kwargs):
    assert _receipt(tool, **kwargs)["result_hash"] == _receipt(tool, **kwargs)["result_hash"]


def test_stamp_without_result_has_no_result_hash():
    assert "result_hash" not in integrity_stamp("core.add", "1.0.0", {"a": 1})


# --- 재실행 검증 ---

def _verify(receipt: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return REGISTRY.invoke(
        "sootool.verify_receipt", tool="finance.loan_schedule", arguments=_LOAN, receipt=receipt, **extra,
    )


def test_genuine_receipt_verifies():
    out = _verify(_receipt())
    assert out["valid"] is True
    assert out["mismatches"] == []


def test_tampered_result_hash_is_reported():
    out = _verify({**_receipt(), "result_hash": "0" * 64})
    assert out["valid"] is False
    assert out["mismatches"] == ["result_hash"]


def test_receipt_for_different_arguments_is_reported():
    out = REGISTRY.invoke(
        "sootool.verify_receipt", tool="finance.loan_schedule",
        arguments={**_LOAN, "months": 24}, receipt=_receipt(),
    )
    assert out["valid"] is False
    assert "input_hash" in out["mismatches"]
    assert "result_hash" in out["mismatches"]


def test_receipt_for_different_tool_is_reported():
    out = REGISTRY.invoke(
        "sootool.verify_receipt", tool="core.add", arguments={"operands": ["1", "2"]}, receipt=_receipt(),
    )
    assert "tool" in out["mismatches"]


def test_tool_version_mismatch_is_reported():
    out = _verify({**_receipt(), "tool_version": "9.9.9"})
    assert out["mismatches"] == ["tool_version"]


def test_missing_required_fields_are_reported():
    receipt = _receipt()
    del receipt["result_hash"]
    assert "result_hash_missing" in _verify(receipt)["mismatches"]


def test_sootool_version_difference_is_only_a_warning():
    out = _verify({**_receipt(), "sootool_version": "0.0.1"})
    assert out["valid"] is True
    assert out["warnings"] == ["sootool_version_differs"]


def test_policy_backed_tool_receipt_roundtrips_and_pins_policy_hash():
    args    = {"taxable_income": "50000000", "year": 2026}
    receipt = _receipt("tax.kr_income", **args)
    assert len(receipt["policy_sha256"]) == 64
    out = REGISTRY.invoke("sootool.verify_receipt", tool="tax.kr_income", arguments=args, receipt=receipt)
    assert out["valid"] is True
    tampered = {**receipt, "policy_sha256": "0" * 64}
    out = REGISTRY.invoke("sootool.verify_receipt", tool="tax.kr_income", arguments=args, receipt=tampered)
    assert out["mismatches"] == ["policy_sha256"]


@pytest.mark.parametrize(
    "tool", ["core.batch", "core.pipeline", "core.pipeline_resume", "sootool.verify_receipt", "sootool.policy_activate"],
)
def test_non_replayable_tools_are_refused(tool):
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("sootool.verify_receipt", tool=tool, arguments={}, receipt={})


def test_bad_arguments_and_receipt_shape_are_typed_errors():
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("sootool.verify_receipt", tool="core.sub", arguments={"a": "1"}, receipt={})
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("sootool.verify_receipt", tool="core.add", arguments={"operands": ["1"]}, receipt="x")


def test_verification_works_through_the_mcp_boundary():
    import asyncio

    srv     = server.build_server()
    receipt = json.loads(json.dumps(_receipt()))
    result = asyncio.run(srv.call_tool(
        "sootool.verify_receipt",
        {"tool": "finance.loan_schedule", "arguments": _LOAN, "receipt": receipt},
    ))
    assert result.structured_content["valid"] is True


# --- 서명 ---

def test_no_key_configured_means_unsigned_stamp():
    stamp = _receipt()
    assert "signature" not in stamp and "signature_error" not in stamp


def test_signing_adds_key_id_and_signature(tmp_path, monkeypatch):
    key_file, _ = _keypair(tmp_path)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    stamp = _receipt()
    assert len(stamp["key_id"]) == 16
    assert stamp["signature"]


def test_signed_receipt_verifies_with_public_key(tmp_path, monkeypatch):
    key_file, public_b64 = _keypair(tmp_path)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    out = _verify(_receipt(), public_key_b64=public_b64)
    assert out["valid"] is True
    assert out["warnings"] == []


def test_signed_receipt_without_public_key_warns(tmp_path, monkeypatch):
    key_file, _ = _keypair(tmp_path)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    out = _verify(_receipt())
    assert out["valid"] is True
    assert "signature_not_checked" in out["warnings"]


def test_signature_from_other_key_is_reported(tmp_path, monkeypatch):
    key_file, _ = _keypair(tmp_path)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    _, other_public = _keypair(other_dir)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    out = _verify(_receipt(), public_key_b64=other_public)
    assert "signature" in out["mismatches"]


def test_tampered_signed_stamp_is_reported(tmp_path, monkeypatch):
    key_file, public_b64 = _keypair(tmp_path)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    receipt = _receipt()
    receipt["key_id"] = "0" * 16
    out = _verify(receipt, public_key_b64=public_b64)
    assert "signature" in out["mismatches"]


def test_malformed_public_key_fails_closed(tmp_path, monkeypatch):
    key_file, _ = _keypair(tmp_path)
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    out = _verify(_receipt(), public_key_b64="not base64 !!")
    assert "signature" in out["mismatches"]


def test_require_signature_rejects_unsigned_receipt():
    out = _verify(_receipt(), require_signature=True)
    assert out["valid"] is False
    assert "signature_missing" in out["mismatches"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [("not base64 !!", "key_malformed"), ("AAAA", "key_malformed")],
)
def test_unusable_key_file_leaves_result_and_records_error(tmp_path, monkeypatch, content, expected):
    key_file = tmp_path / "bad.key"
    key_file.write_text(content, encoding="ascii")
    monkeypatch.setenv(SIGNING_KEY_ENV, str(key_file))
    out = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert out["result"] == "3"
    assert out["_meta"]["integrity"]["signature_error"] == expected
    assert "signature" not in out["_meta"]["integrity"]


def test_missing_key_file_leaves_result_and_records_error(tmp_path, monkeypatch):
    monkeypatch.setenv(SIGNING_KEY_ENV, str(tmp_path / "absent.key"))
    out = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert out["_meta"]["integrity"]["signature_error"] == "key_file_unreadable"


def test_sign_stamp_is_a_noop_without_configuration():
    stamp = {"tool": "core.add"}
    assert sign_stamp(stamp) == stamp
