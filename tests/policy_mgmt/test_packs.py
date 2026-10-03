"""외부 정책 팩 생성, 검증, 설치 시험.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sootool import server
from sootool.cli.main import run
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.policy_mgmt import packs
from sootool.policy_mgmt.paths import get_override_policy_dir


def _keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    private_b64 = base64.b64encode(private.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption(),
    )).decode("ascii")
    public_b64 = base64.b64encode(private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )).decode("ascii")
    return private_b64, public_b64


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    private_b64, public_b64 = _keypair()
    key_file = tmp_path / "publisher.key"
    key_file.write_text(private_b64, encoding="ascii")
    os.chmod(key_file, 0o600)
    monkeypatch.setenv("SOOTOOL_POLICY_KEY_FILE", str(key_file))
    server._load_modules()
    return {"public": public_b64, "tmp": tmp_path}


def _signed_pack() -> dict:
    bundles = [
        REGISTRY.invoke("sootool.policy_export", domain="tax", name=name, year=2026, include_signature=True)["bundle"]
        for name in ("kr_income", "kr_gift")
    ]
    manifest = {"name": "kr-sample-pack", "version": "1.0.0", "publisher": "sample-reviewer", "description": "시험용 팩"}
    return packs.build_pack(manifest, bundles)


def test_built_pack_verifies_and_lists_its_bundles(env):
    summary = packs.verify_pack(_signed_pack(), env["public"])
    assert summary == [{"domain": "tax", "name": "kr_income", "year": 2026}, {"domain": "tax", "name": "kr_gift", "year": 2026}]


def test_tampered_manifest_is_rejected(env):
    pack = _signed_pack()
    pack["manifest"]["version"] = "9.9.9"
    with pytest.raises(packs.PackVerificationError):
        packs.verify_pack(pack, env["public"])


def test_tampered_bundle_is_rejected(env):
    pack = _signed_pack()
    pack["bundles"][0]["yaml_content"] += "\n# tampered\n"
    with pytest.raises(packs.PackVerificationError):
        packs.verify_pack(pack, env["public"])


def test_dropped_bundle_is_rejected(env):
    pack = _signed_pack()
    pack["bundles"].pop()
    with pytest.raises(packs.PackVerificationError):
        packs.verify_pack(pack, env["public"])


def test_other_publisher_key_is_rejected(env):
    _, other_public = _keypair()
    with pytest.raises(packs.PackVerificationError):
        packs.verify_pack(_signed_pack(), other_public)


@pytest.mark.parametrize("mutate", [
    lambda p: p.pop("signature"),
    lambda p: p.update(format=2),
    lambda p: p["manifest"].pop("publisher"),
    lambda p: p.update(bundles=[]),
    lambda p: p["bundles"][0].pop("signature"),
])
def test_malformed_packs_are_rejected(env, mutate):
    pack = copy.deepcopy(_signed_pack())
    mutate(pack)
    with pytest.raises(InvalidInputError):
        packs.verify_pack(pack, env["public"])


def test_build_requires_a_key_file(env, monkeypatch):
    pack = _signed_pack()
    monkeypatch.delenv("SOOTOOL_POLICY_KEY_FILE")
    with pytest.raises(InvalidInputError):
        packs.build_pack(pack["manifest"], pack["bundles"])


def test_install_imports_every_bundle_through_the_admin_gate(env, monkeypatch):
    pack = _signed_pack()
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    denied = packs.install_pack(pack, env["public"])
    assert denied[0]["installed"] is False and denied[0]["outcome"]["error"] == "admin_required"

    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    results = packs.install_pack(pack, env["public"])
    assert [r["installed"] for r in results] == [True, True]
    installed = {p.name for p in (get_override_policy_dir() / "tax").glob("*.yaml")}
    assert {"kr_income_2026.yaml", "kr_gift_2026.yaml"} <= installed


def test_cli_verify_and_install(env, monkeypatch, capsys):
    pack_file = Path(env["tmp"]) / "pack.json"
    pack_file.write_text(json.dumps(_signed_pack(), ensure_ascii=False), encoding="utf-8")

    assert run(["pack", "verify", str(pack_file), "--public-key", env["public"], "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["verified"] is True

    _, other_public = _keypair()
    assert run(["pack", "verify", str(pack_file), "--public-key", other_public]) == 2

    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    assert run(["pack", "install", str(pack_file), "--public-key", env["public"]]) == 3
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    assert run(["pack", "install", str(pack_file), "--public-key", env["public"]]) == 0


def test_cli_build_writes_a_verifiable_pack(env, capsys):
    pack = _signed_pack()
    manifest_file = Path(env["tmp"]) / "manifest.json"
    manifest_file.write_text(json.dumps(pack["manifest"]), encoding="utf-8")
    bundle_files = []
    for index, bundle in enumerate(pack["bundles"]):
        path = Path(env["tmp"]) / f"bundle{index}.json"
        path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        bundle_files += ["--bundle", str(path)]
    assert run(["pack", "build", "--manifest", str(manifest_file), *bundle_files]) == 0
    built = json.loads(capsys.readouterr().out)
    assert len(packs.verify_pack(built, env["public"])) == 2
