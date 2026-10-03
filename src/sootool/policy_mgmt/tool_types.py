"""정책 관리 도구의 결과 타입.

조회 도구(``tools_read``)와 쓰기 도구(``tools_write``)가 공유한다. 쓰기 도구는 관리자 모드가 아니거나
검증에 실패하면 성공 응답 대신 ``error`` 와 ``message`` 를 가진 응답을 돌려주므로, 분기마다 달라지는
필드는 모두 선택 필드로 선언한다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from sootool.core.result_types import PolicyVersion, ToolResult


class ValidationFinding(TypedDict):
    level:   str
    path:    str
    message: str
    stage:   int


class ValidationReport(TypedDict):
    """검증 파이프라인 보고서. ``fixed_sha256`` 은 auto_fix_sha256 요청 시에만 있다."""

    status:       str
    findings:     list[ValidationFinding]
    sha256:       NotRequired[str]
    fixed_sha256: NotRequired[str]


class PolicyChange(TypedDict):
    """정책 두 버전의 변경점 하나. 구간 변경은 ``bracket``, 값 변경은 ``field`` 를 가진다."""

    type:       str
    bracket:    NotRequired[str]
    field:      NotRequired[str]
    old:        NotRequired[str]
    new:        NotRequired[str]
    delta:      NotRequired[str]
    old_rate:   NotRequired[str]
    new_rate:   NotRequired[str]
    pct_change: NotRequired[str]


class PolicyDiff(TypedDict):
    vs_year:      int
    current_year: int
    changes:      list[PolicyChange]
    summary:      str


class PolicyDiffResult(ToolResult):
    """비교할 수 없으면 ``error`` 만 있고, 비교했으면 나머지 필드가 있다."""

    vs_year:      NotRequired[int]
    current_year: NotRequired[int]
    changes:      NotRequired[list[PolicyChange]]
    summary:      NotRequired[str]
    error:        NotRequired[str]


class PolicyListEntry(TypedDict):
    domain:         str
    name:           str
    year:           int
    source:         str
    sha256:         str
    effective_date: str
    effective_to:   str | None
    status:         str
    version:        str | None
    is_active:      bool
    is_override:    bool
    path:           str


class PolicyListResult(ToolResult):
    policies: list[PolicyListEntry]
    count:    int


class PolicyGetResult(ToolResult):
    domain:         str
    name:           str
    year:           int
    source:         str
    data:           Any
    policy_version: PolicyVersion


class PolicyAuditEntry(TypedDict):
    ts:            str
    audit_id:      str
    actor:         str
    action:        str
    domain:        str
    name:          str
    year:          int
    draft_id:      str | None
    sha256_before: str | None
    sha256_after:  str | None
    source_url:    str | None
    notice_no:     str | None
    validation:    ValidationReport


class PolicyHistoryResult(ToolResult):
    domain:  str
    name:    str
    entries: list[PolicyAuditEntry]
    count:   int


class PolicyValidateResult(ValidationReport, ToolResult):
    pass


class PolicyBundleMetadata(TypedDict):
    domain:         str
    name:           str
    year:           int
    source:         str
    policy_version: PolicyVersion


class PolicyBundle(TypedDict):
    yaml_content: str
    metadata:     PolicyBundleMetadata
    signature:    NotRequired[str]


class PolicyExportResult(ToolResult):
    bundle: PolicyBundle


AdminRequired = Literal["admin_required"]


class PolicyProposeResult(ToolResult):
    draft_id:   NotRequired[str]
    domain:     NotRequired[str]
    name:       NotRequired[str]
    year:       NotRequired[int]
    validation: NotRequired[ValidationReport]
    diff:       NotRequired[PolicyDiff | None]
    expires_at: NotRequired[float]
    error:      NotRequired[AdminRequired]
    message:    NotRequired[str]


class PolicyActivateResult(ToolResult):
    activated:  NotRequired[bool]
    domain:     NotRequired[str]
    name:       NotRequired[str]
    year:       NotRequired[int]
    source:     NotRequired[str]
    audit_id:   NotRequired[str]
    sha256:     NotRequired[str]
    validation: NotRequired[ValidationReport]
    error:      NotRequired[Literal["admin_required", "validation_failed"]]
    message:    NotRequired[str]


class PolicyRollbackResult(ToolResult):
    rolled_back: NotRequired[bool]
    domain:      NotRequired[str]
    name:        NotRequired[str]
    year:        NotRequired[int]
    audit_id:    NotRequired[str]
    versions:    NotRequired[list[str]]
    error:       NotRequired[Literal["admin_required", "ambiguous_version"]]
    message:     NotRequired[str]


class PolicyImportResult(ToolResult):
    imported:   NotRequired[bool]
    domain:     NotRequired[str]
    name:       NotRequired[str]
    year:       NotRequired[int]
    audit_id:   NotRequired[str]
    sha256:     NotRequired[str]
    validation: NotRequired[ValidationReport]
    error:      NotRequired[
        Literal["admin_required", "signature_required", "signature_invalid", "invalid_bundle", "validation_failed"]
    ]
    message:    NotRequired[str]
