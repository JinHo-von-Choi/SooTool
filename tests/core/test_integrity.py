"""Tests for ADR-021 deterministic reproducibility stamp (_meta.integrity).

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import json

import pytest

import sootool.server as _server
from sootool.core.audit import (
    _canonical_json,
    integrity_stamp,
    reset_integrity_ctx,
    set_current_inputs,
    set_policy_meta,
)
from sootool.core.registry import REGISTRY

_server._load_modules()  # ensure tax.* etc. are registered for these tests


@pytest.fixture(autouse=True)
def _clear_integrity_ctx():
    """Reset thread-local integrity state before and after each test."""
    reset_integrity_ctx()
    yield
    reset_integrity_ctx()


class TestCanonicalJson:
    def test_key_order_insensitive_hash(self) -> None:
        a = {"b": 1, "a": 2}
        b = {"a": 2, "b": 1}
        assert _canonical_json(a) == _canonical_json(b)

    def test_decimal_normalized_as_string(self) -> None:
        from decimal import Decimal
        c1 = _canonical_json({"x": Decimal("1.50")})
        c2 = _canonical_json({"x": "1.50"})
        assert c1 == c2


class TestIntegrityStamp:
    def test_same_inputs_produce_same_hash(self) -> None:
        s1 = integrity_stamp("t.x", "1.0.0", {"a": 1, "b": "two"})
        s2 = integrity_stamp("t.x", "1.0.0", {"a": 1, "b": "two"})
        assert s1["input_hash"] == s2["input_hash"]

    def test_reordered_keys_same_hash(self) -> None:
        s1 = integrity_stamp("t.x", "1.0.0", {"a": 1, "b": "two"})
        s2 = integrity_stamp("t.x", "1.0.0", {"b": "two", "a": 1})
        assert s1["input_hash"] == s2["input_hash"]

    def test_different_inputs_different_hash(self) -> None:
        s1 = integrity_stamp("t.x", "1.0.0", {"a": 1})
        s2 = integrity_stamp("t.x", "1.0.0", {"a": 2})
        assert s1["input_hash"] != s2["input_hash"]

    def test_input_hash_matches_manual_sha256(self) -> None:
        inputs = {"a": 1, "b": "two"}
        canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        stamp = integrity_stamp("t.x", "1.0.0", inputs)
        assert stamp["input_hash"] == expected

    def test_empty_inputs_hashable(self) -> None:
        stamp = integrity_stamp("t.x", "1.0.0", None)
        assert stamp["input_hash"] == hashlib.sha256(b"{}").hexdigest()

    def test_sootool_version_field_present(self) -> None:
        stamp = integrity_stamp("t.x", "1.2.3", {})
        assert "sootool_version" in stamp
        assert isinstance(stamp["sootool_version"], str)

    def test_policy_fields_omitted_when_no_policy(self) -> None:
        stamp = integrity_stamp("t.x", "1.0.0", {})
        assert "policy_sha256" not in stamp
        assert "policy_source" not in stamp

    def test_policy_fields_present_when_policy_supplied(self) -> None:
        stamp = integrity_stamp(
            "tax.kr_income",
            "1.0.0",
            {"year": 2026},
            policy_meta={
                "policy_sha256": "abc123",
                "policy_source": "tax/kr_income/2026",
            },
        )
        assert stamp["policy_sha256"] == "abc123"
        assert stamp["policy_source"] == "tax/kr_income/2026"


class TestPostProcessorInjection:
    def test_core_add_has_integrity(self) -> None:
        resp = REGISTRY.invoke("core.add", operands=["1", "2"])
        assert "_meta" in resp
        assert "integrity" in resp["_meta"]
        stamp = resp["_meta"]["integrity"]
        assert "input_hash" in stamp
        assert "tool_version" in stamp
        assert "sootool_version" in stamp

    def test_core_add_reproducible(self) -> None:
        r1 = REGISTRY.invoke("core.add", operands=["1", "2"])
        r2 = REGISTRY.invoke("core.add", operands=["1", "2"])
        assert r1["_meta"]["integrity"]["input_hash"] == r2["_meta"]["integrity"]["input_hash"]

    def test_core_add_lacks_policy_fields(self) -> None:
        """Tools that do not use any policy must not emit policy_sha256."""
        resp = REGISTRY.invoke("core.add", operands=["1", "2"])
        stamp = resp["_meta"]["integrity"]
        assert "policy_sha256" not in stamp
        assert "policy_source" not in stamp

    def test_result_and_trace_unchanged(self) -> None:
        """ADR-011 invariant: result and trace fields are never mutated."""
        resp = REGISTRY.invoke("core.add", operands=["1", "2"])
        assert resp["result"] == "3"
        assert resp["trace"]["tool"] == "core.add"
        # The trace block itself must carry no integrity data.
        assert "integrity" not in resp["trace"]


class TestPolicyToolIntegrity:
    def test_tax_kr_income_integrity_has_policy_sha256(self) -> None:
        resp = REGISTRY.invoke(
            "tax.kr_income",
            taxable_income="50000000",
            year=2026,
        )
        assert "_meta" in resp
        assert "integrity" in resp["_meta"]
        stamp = resp["_meta"]["integrity"]
        # Policy fields must be populated.
        assert "policy_sha256" in stamp
        assert "policy_source" in stamp
        assert stamp["policy_source"] == "tax/kr_income/2026"

    def test_policy_sha256_matches_yaml(self) -> None:
        resp = REGISTRY.invoke(
            "tax.kr_income",
            taxable_income="50000000",
            year=2026,
        )
        stamp_sha = resp["_meta"]["integrity"]["policy_sha256"]
        # Response also carries policy_sha256 at top level via trace_ext.
        assert resp["policy_sha256"] == stamp_sha

    def test_tax_kr_income_reproducible_with_policy(self) -> None:
        r1 = REGISTRY.invoke("tax.kr_income", taxable_income="50000000", year=2026)
        r2 = REGISTRY.invoke("tax.kr_income", taxable_income="50000000", year=2026)
        assert r1["_meta"]["integrity"]["input_hash"] == r2["_meta"]["integrity"]["input_hash"]
        assert r1["_meta"]["integrity"]["policy_sha256"] == r2["_meta"]["integrity"]["policy_sha256"]


class TestBatchPipelineIntegrity:
    def test_batch_individual_results_have_integrity(self) -> None:
        resp = REGISTRY.invoke(
            "core.batch",
            items=[
                {"id": "a", "tool": "core.add", "args": {"operands": ["1", "2"]}},
                {"id": "b", "tool": "core.add", "args": {"operands": ["3", "4"]}},
            ],
        )
        assert resp["status"] == "all_ok"
        for item in resp["results"]:
            inner = item["result"]
            assert "_meta" in inner
            assert "integrity" in inner["_meta"]
            assert "input_hash" in inner["_meta"]["integrity"]

    def test_batch_same_args_same_hash(self) -> None:
        resp = REGISTRY.invoke(
            "core.batch",
            items=[
                {"id": "a", "tool": "core.add", "args": {"operands": ["1", "2"]}},
                {"id": "b", "tool": "core.add", "args": {"operands": ["1", "2"]}},
            ],
        )
        assert resp["status"] == "all_ok"
        hashes = [r["result"]["_meta"]["integrity"]["input_hash"] for r in resp["results"]]
        assert hashes[0] == hashes[1]

    def test_pipeline_step_results_have_integrity(self) -> None:
        resp = REGISTRY.invoke(
            "core.pipeline",
            steps=[
                {"id": "s1", "tool": "core.add",
                 "args": {"operands": ["1", "2"]}},
                {"id": "s2", "tool": "core.mul",
                 "args": {"operands": ["${s1.result.result}", "3"]}},
            ],
        )
        assert resp["status"] == "ok"
        for step_id in ("s1", "s2"):
            inner = resp["steps"][step_id]["result"]
            assert "_meta" in inner
            assert "integrity" in inner["_meta"]


class TestIntegrityCtxIsolation:
    def test_ctx_cleared_after_invoke(self) -> None:
        """Nested invoke must not leak state into the outer frame."""
        from sootool.core.audit import _INTEGRITY_CTX
        set_current_inputs({"outer": 1})
        set_policy_meta("override", "sha_outer", "tax", "kr_income", 2026)
        # Inner invoke: this clobbers thread-local inputs during the call.
        REGISTRY.invoke("core.add", operands=["1", "2"])
        # Outer context must be restored.
        assert _INTEGRITY_CTX.inputs == {"outer": 1}
        assert _INTEGRITY_CTX.policy_meta is not None
        assert _INTEGRITY_CTX.policy_meta.get("policy_sha256") == "sha_outer"


class TestSmokeResponseShape:
    def test_response_keys_preserved(self) -> None:
        """A realistic tool response must retain its public contract keys."""
        resp = REGISTRY.invoke("core.add", operands=["1", "2"])
        assert set(resp.keys()) >= {"result", "trace", "_meta"}
        assert "integrity" in resp["_meta"]
