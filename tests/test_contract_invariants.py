"""안정성 계약(docs/stability.md)의 불변 조건을 구조 검사로 확인한다.

값이나 응답 전체를 고정하지 않고, 이름 형식, 버전 형식, 폐기 선언의 정합성, 오류 코드와 영수증 필드,
공개 SDK 이름처럼 호환 약속의 대상이 지켜지는지만 본다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import re

import pytest

from sootool import sdk, server
from sootool.core import errors
from sootool.core.receipts import REQUIRED_FIELDS
from sootool.core.registry import REGISTRY
from sootool.runtime import NAMESPACE_MODULES

_NAME = re.compile(r"[a-z][a-z_]*\.[A-Za-z][A-Za-z0-9_]*")
_SEMVER = re.compile(r"\d+\.\d+\.\d+")
# 호환 약속 대상 오류 코드. 코드의 추가는 호환 변경이지만 제거와 이름 변경은 아니다.
_PROMISED_ERROR_CODES = frozenset({
    "invalid_input", "invalid_arguments", "invalid_number", "unknown_tool", "domain_constraint", "division_by_zero",
    "input_limit", "timeout", "policy_not_in_effect", "policy_not_enacted", "policy_format", "tool_error",
})


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def test_tool_names_and_versions_are_well_formed():
    for entry in REGISTRY.list():
        assert _NAME.fullmatch(entry.full_name), entry.full_name
        assert _SEMVER.fullmatch(entry.version), entry.full_name
        assert entry.namespace in NAMESPACE_MODULES, entry.full_name


def test_deprecations_name_an_existing_replacement_and_a_removal_version():
    names = {e.full_name for e in REGISTRY.list()}
    for entry in REGISTRY.list():
        if entry.deprecated:
            replacement = entry.deprecated.get("replacement")
            assert replacement is None or replacement in names, entry.full_name
            assert _SEMVER.fullmatch(str(entry.deprecated.get("remove_in", ""))), entry.full_name


def test_promised_error_codes_still_exist():
    codes = {
        getattr(cls, "code", None)
        for cls in vars(errors).values()
        if isinstance(cls, type) and issubclass(cls, errors.SooToolError)
    }
    assert _PROMISED_ERROR_CODES <= codes, _PROMISED_ERROR_CODES - codes


def test_internal_error_code_is_stable():
    from sootool.boundary import INTERNAL_ERROR_CODE

    assert INTERNAL_ERROR_CODE == "internal_error"


def test_receipt_required_fields_are_stable():
    assert set(REQUIRED_FIELDS) == {"tool", "input_hash", "result_hash", "tool_version"}


def test_every_calculation_result_declares_a_typed_result_with_optional_extras_allowed():
    from sootool.core.result_types import declared_result_type

    untyped = [e.full_name for e in REGISTRY.list() if declared_result_type(e.fn) is None]
    assert not untyped, untyped


def test_public_sdk_names_exist():
    assert {"Namespace", "Tool", "namespaces"} <= set(sdk.__all__)
    assert set(sdk.namespaces()) == set(NAMESPACE_MODULES)
