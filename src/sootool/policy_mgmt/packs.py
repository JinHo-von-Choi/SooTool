"""외부 정책 팩: 서명된 정책 번들 묶음의 생성, 검증, 설치.

팩은 제공자가 만든 JSON 파일이다. ``manifest``(이름, 버전, 제공자, 설명)와 ``bundles``(``sootool.policy_export`` 가
만든 번들, 각각 ed25519 서명 포함), 그리고 manifest 와 번들 해시 목록 전체에 대한 팩 서명을 가진다. 설치는 검증 뒤
번들마다 ``sootool.policy_import`` 를 거치므로 관리자 게이트, 정책 스키마 검증, 감사 기록이 그대로 적용된다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Final

from sootool.core.errors import InvalidInputError
from sootool.core.signing import (
    SignatureVerificationError,
    load_private_key_file,
    sign_with,
    verify_bytes,
)
from sootool.policy_mgmt.signatures import bundle_payload_bytes, verify_bundle

PACK_FORMAT: Final = 1
POLICY_KEY_ENV: Final = "SOOTOOL_POLICY_KEY_FILE"
_MANIFEST_KEYS: Final = ("name", "version", "publisher")


class PackVerificationError(InvalidInputError):
    """팩의 구조나 서명이 올바르지 않다."""


def _pack_payload(manifest: dict[str, Any], bundles: list[dict[str, Any]]) -> bytes:
    """팩 서명 대상: 정규화한 manifest 와 번들별 sha256 목록."""
    digests = [
        hashlib.sha256(bundle_payload_bytes(b["yaml_content"], b["metadata"])).hexdigest() for b in bundles
    ]
    body = {"format": PACK_FORMAT, "manifest": manifest, "bundle_digests": digests}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _check_structure(pack: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(pack, dict) or pack.get("format") != PACK_FORMAT:
        raise PackVerificationError(f"정책 팩 형식(format={PACK_FORMAT})이 아닙니다.")
    manifest = pack.get("manifest")
    bundles  = pack.get("bundles")
    if not isinstance(manifest, dict) or any(not isinstance(manifest.get(k), str) or not manifest[k] for k in _MANIFEST_KEYS):
        raise PackVerificationError(f"manifest 에는 {', '.join(_MANIFEST_KEYS)} 가 문자열로 있어야 합니다.")
    if not isinstance(bundles, list) or not bundles:
        raise PackVerificationError("bundles 는 비어 있지 않은 목록이어야 합니다.")
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict) or not isinstance(bundle.get("yaml_content"), str) \
                or not isinstance(bundle.get("metadata"), dict) or not isinstance(bundle.get("signature"), str):
            raise PackVerificationError(f"bundles[{index}] 는 yaml_content, metadata, signature 를 가져야 합니다.")
    return manifest, bundles


def build_pack(manifest: dict[str, Any], bundles: list[dict[str, Any]]) -> dict[str, Any]:
    """번들을 묶어 팩을 만들고 팩 서명을 붙인다. 서명 키는 환경변수 SOOTOOL_POLICY_KEY_FILE 의 파일에서 읽는다."""
    key_file = os.environ.get(POLICY_KEY_ENV, "").strip()
    if not key_file:
        raise InvalidInputError(f"팩을 서명하려면 환경변수 {POLICY_KEY_ENV} 에 키 파일 경로를 설정해야 합니다.")
    pack: dict[str, Any] = {"format": PACK_FORMAT, "manifest": manifest, "bundles": bundles}
    _check_structure({**pack, "signature": "-"})
    pack["signature"] = sign_with(load_private_key_file(key_file), _pack_payload(manifest, bundles))
    return pack


def verify_pack(pack: Any, public_key_b64: str) -> list[dict[str, Any]]:
    """팩 서명과 모든 번들 서명을 검증하고 번들 요약(영역, 이름, 연도) 목록을 반환한다."""
    manifest, bundles = _check_structure(pack)
    signature = pack.get("signature")
    if not isinstance(signature, str) or not signature:
        raise PackVerificationError("팩 서명이 없습니다.")
    try:
        verify_bytes(_pack_payload(manifest, bundles), signature, public_key_b64)
        for index, bundle in enumerate(bundles):
            try:
                verify_bundle(bundle_payload_bytes(bundle["yaml_content"], bundle["metadata"]), bundle["signature"], public_key_b64)
            except SignatureVerificationError as exc:
                raise PackVerificationError(f"bundles[{index}] 서명이 올바르지 않습니다: {exc}") from exc
    except SignatureVerificationError as exc:
        raise PackVerificationError(f"팩 서명이 올바르지 않습니다: {exc}") from exc
    return [
        {"domain": b["metadata"].get("domain"), "name": b["metadata"].get("name"), "year": b["metadata"].get("year")}
        for b in bundles
    ]


def install_pack(pack: Any, public_key_b64: str) -> list[dict[str, Any]]:
    """검증을 통과한 팩의 번들을 하나씩 가져온다. 하나라도 가져오기에 실패하면 거기서 멈추고 결과를 돌려준다."""
    from sootool.core.registry import REGISTRY

    summaries = verify_pack(pack, public_key_b64)
    results: list[dict[str, Any]] = []
    for summary, bundle in zip(summaries, pack["bundles"], strict=True):
        outcome = REGISTRY.invoke(
            "sootool.policy_import", bundle=bundle, require_signature=True, public_key_b64=public_key_b64,
        )
        failed = "error" in outcome
        results.append({**summary, "installed": not failed, "outcome": outcome})
        if failed:
            break
    return results
