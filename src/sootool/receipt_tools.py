"""sootool.verify_receipt: 계산 영수증의 재실행 검증.

이전 응답의 ``_meta.integrity`` (영수증)와 원래 입력을 받아 같은 도구를 다시 실행하고,
도구 이름, 입력 해시, 결과 해시, 도구 버전, 정책 해시가 일치하는지 대조한다. 서명이 있고
공개 키가 주어지면 서명도 검증한다. 결정적 엔진이므로 같은 입력은 같은 결과 해시를 낸다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.catalog import bind_call_arguments, resolve_tool
from sootool.core.errors import InvalidInputError
from sootool.core.receipts import (
    COMPARED_FIELDS,
    NON_REPLAYABLE_TOOLS,
    REQUIRED_FIELDS,
    verify_stamp_signature,
)
from sootool.core.registry import REGISTRY
from sootool.core.signing import SignatureVerificationError


@REGISTRY.tool(
    namespace="sootool",
    name="verify_receipt",
    description=(
        "계산 영수증(_meta.integrity)을 재실행으로 검증한다. tool 과 arguments 로 같은 계산을 "
        "다시 실행해 입력 해시, 결과 해시, 도구 버전, 정책 해시를 대조하고, 서명이 있으면 "
        "public_key_b64 로 서명을 검증한다. valid 와 mismatches 를 반환한다."
    ),
    version="1.0.0",
)
def verify_receipt(
    tool:              str,
    arguments:         dict[str, Any],
    receipt:           dict[str, Any],
    public_key_b64:    str | None = None,
    require_signature: bool       = False,
) -> dict[str, Any]:
    """Re-execute ``tool`` with ``arguments`` and compare against ``receipt``."""
    trace = CalcTrace(tool="sootool.verify_receipt", formula="replay(tool, arguments) == receipt")
    if not isinstance(receipt, dict):
        raise InvalidInputError("receipt 는 객체(_meta.integrity)여야 합니다.")

    entry = resolve_tool(REGISTRY, tool)
    if entry.full_name in NON_REPLAYABLE_TOOLS or not entry.read_only:
        raise InvalidInputError(f"{entry.full_name} 은(는) 재실행 검증 대상이 아닙니다.")
    kwargs = bind_call_arguments(entry, arguments)

    fresh = REGISTRY.invoke(entry.full_name, **kwargs)
    recomputed = fresh.get("_meta", {}).get("integrity") if isinstance(fresh, dict) else None
    if not isinstance(recomputed, dict):
        raise InvalidInputError(f"{entry.full_name} 은(는) 영수증을 생성하지 않는 도구입니다.")

    mismatches: list[str] = []
    warnings:   list[str] = []

    for name in COMPARED_FIELDS:
        if name in REQUIRED_FIELDS and name not in receipt:
            mismatches.append(f"{name}_missing")
        elif receipt.get(name) != recomputed.get(name):
            mismatches.append(name)

    if receipt.get("sootool_version") != recomputed.get("sootool_version"):
        warnings.append("sootool_version_differs")

    if "signature" in receipt:
        if public_key_b64:
            try:
                verify_stamp_signature(receipt, public_key_b64)
            except SignatureVerificationError:
                mismatches.append("signature")
        else:
            warnings.append("signature_not_checked")
    elif require_signature:
        mismatches.append("signature_missing")

    valid = not mismatches
    trace.input("tool", entry.full_name)
    trace.input("input_hash", recomputed.get("input_hash"))
    trace.step("mismatches", mismatches)
    trace.output(valid)

    return {
        "valid":      valid,
        "mismatches": mismatches,
        "warnings":   warnings,
        "recomputed": recomputed,
        "trace":      trace.to_dict(),
    }
