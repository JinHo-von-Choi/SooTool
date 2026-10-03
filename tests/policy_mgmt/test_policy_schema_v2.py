"""정책 헤더 v2(status, effective_to, citations, reviewed_by) 검증과 버전 관리 도구 흐름."""
from __future__ import annotations

from pathlib import Path

import pytest

from sootool import server
from sootool.core.registry import REGISTRY
from sootool.policies import _compute_sha256
from sootool.policy_mgmt import loader
from sootool.policy_mgmt.validators import validate_policy


def _doc(
    *,
    effective_date: str = "2031-01-01",
    effective_to:   str | None = None,
    status:         str | None = None,
    citations:      str | None = '  - law: "소득세법"\n    article: "제55조"',
    extra:          str = "",
    rate:           str = "0.10",
) -> str:
    lines = [f'effective_date: "{effective_date}"']
    if effective_to:
        lines.append(f'effective_to: "{effective_to}"')
    if status:
        lines.append(f"status: {status}")
    lines += ['notice_no: "시험"', 'source_url: "https://example.invalid"']
    if citations is not None:
        lines.append("citations:" if citations else "citations: []")
        if citations:
            lines.append(citations)
    if extra:
        lines.append(extra)
    lines += ["data:", "  brackets:", "    - upper: null", f"      rate: {rate}"]
    body = "\n".join(lines) + "\n"
    return f'sha256: "{_compute_sha256(body)}"\n{body}'


def _findings(report, path: str, level: str | None = None):
    return [f for f in report["findings"] if f["path"].startswith(path) and (level is None or f["level"] == level)]


# --- 헤더 v2 검증 ---

def test_valid_v2_header_has_no_header_findings():
    report = validate_policy(_doc(effective_to="2031-12-31", extra='reviewed_by: ["세무사 시험"]'),
                             domain="tax", name="kr_income")
    assert not _findings(report, "citations") and not _findings(report, "status")
    assert report["status"] == "ok"


def test_missing_citations_is_a_warning_for_enacted_and_an_error_for_proposed():
    enacted  = validate_policy(_doc(citations=None), domain="tax", name="kr_income")
    proposed = validate_policy(_doc(citations=None, status="proposed"), domain="tax", name="kr_income")
    assert _findings(enacted, "citations", "warning") and not _findings(enacted, "citations", "error")
    assert _findings(proposed, "citations", "error")
    assert proposed["status"] == "error"


@pytest.mark.parametrize("status", ["draft", "ENACTED", "pending"])
def test_unknown_status_is_an_error(status):
    report = validate_policy(_doc(status=status), domain="tax", name="kr_income")
    assert _findings(report, "status", "error")


def test_effective_to_must_not_precede_effective_date():
    report = validate_policy(_doc(effective_date="2031-06-01", effective_to="2031-01-01"),
                             domain="tax", name="kr_income")
    assert _findings(report, "effective_to", "error")


def test_non_iso_dates_are_errors():
    report = validate_policy(_doc(effective_date="2031/01/01"), domain="tax", name="kr_income")
    assert _findings(report, "effective_date", "error")
    report = validate_policy(_doc(effective_to="내년 말"), domain="tax", name="kr_income")
    assert _findings(report, "effective_to", "error")


@pytest.mark.parametrize(
    "citations",
    [
        '  - article: "제55조"',
        '  - law: ""',
        '  - law: "소득세법"\n    clause: "1항"',
        '  - "소득세법 제55조"',
    ],
)
def test_malformed_citation_entries_are_errors(citations):
    report = validate_policy(_doc(citations=citations), domain="tax", name="kr_income")
    assert _findings(report, "citations[", "error")


def test_citations_must_be_a_list():
    report = validate_policy(_doc(citations="  law: 소득세법"), domain="tax", name="kr_income")
    assert _findings(report, "citations", "error")


def test_reviewed_by_must_be_a_list_of_strings():
    report = validate_policy(_doc(extra="reviewed_by: 홍길동"), domain="tax", name="kr_income")
    assert _findings(report, "reviewed_by", "error")


# --- 버전 겹침 검사와 관리 도구 흐름 ---

@pytest.fixture
def admin_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    server._load_modules()
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    loader.invalidate_cache()
    yield tmp_path / "policies" / "tax"
    loader.invalidate_cache()


def _activate(yaml_text: str, year: int = 2031) -> dict:
    proposed = REGISTRY.invoke("sootool.policy_propose", domain="tax", name="kr_income", year=year, yaml_content=yaml_text)
    assert proposed["validation"]["status"] != "error", proposed["validation"]
    return REGISTRY.invoke("sootool.policy_activate", draft_id=proposed["draft_id"])


def test_a_new_effective_date_creates_a_second_version_file(admin_env):
    _activate(_doc(effective_date="2031-01-01", effective_to="2031-06-30", rate="0.10"))
    _activate(_doc(effective_date="2031-07-01", rate="0.20"))
    names = sorted(p.name for p in admin_env.glob("kr_income_2031*.yaml"))
    assert names == ["kr_income_2031.yaml", "kr_income_2031@2031-07-01.yaml"]

    early = REGISTRY.invoke("tax.kr_income", taxable_income="10000000", year=2031, as_of="2031-03-01")
    late  = REGISTRY.invoke("tax.kr_income", taxable_income="10000000", year=2031, as_of="2031-09-01")
    assert (early["tax"], late["tax"]) == ("1000000", "2000000")


def test_the_same_effective_date_replaces_the_version_in_place(admin_env):
    _activate(_doc(effective_date="2031-01-01", rate="0.10"))
    _activate(_doc(effective_date="2031-01-01", rate="0.15"))
    assert [p.name for p in admin_env.glob("kr_income_2031*.yaml")] == ["kr_income_2031.yaml"]
    assert REGISTRY.invoke("tax.kr_income", taxable_income="10000000", year=2031)["tax"] == "1500000"


def test_overlapping_enacted_periods_are_rejected_at_propose_time(admin_env):
    _activate(_doc(effective_date="2031-01-01", rate="0.10"))
    report = validate_policy(_doc(effective_date="2031-07-01", rate="0.20"), domain="tax", name="kr_income")
    overlap = _findings(report, "effective_date", "error")
    assert overlap and "overlaps" in overlap[0]["message"]


def test_closing_the_earlier_version_makes_the_new_one_valid(admin_env):
    _activate(_doc(effective_date="2031-01-01", effective_to="2031-06-30", rate="0.10"))
    report = validate_policy(_doc(effective_date="2031-07-01", rate="0.20"), domain="tax", name="kr_income")
    assert not _findings(report, "effective_date", "error")


def test_a_proposed_version_may_overlap_an_enacted_one(admin_env):
    _activate(_doc(effective_date="2031-01-01", rate="0.10"))
    report = validate_policy(_doc(effective_date="2031-07-01", status="proposed", rate="0.40"),
                             domain="tax", name="kr_income")
    assert not _findings(report, "effective_date", "error")


def test_rollback_by_effective_date_removes_only_that_version(admin_env):
    _activate(_doc(effective_date="2031-01-01", effective_to="2031-06-30", rate="0.10"))
    _activate(_doc(effective_date="2031-07-01", rate="0.20"))

    ambiguous = REGISTRY.invoke("sootool.policy_rollback", domain="tax", name="kr_income", year=2031)
    assert ambiguous["error"] == "ambiguous_version"
    assert ambiguous["versions"] == ["2031-01-01", "2031-07-01"]

    out = REGISTRY.invoke("sootool.policy_rollback", domain="tax", name="kr_income", year=2031,
                          effective_date="2031-07-01")
    assert out["rolled_back"] is True
    assert [p.name for p in admin_env.glob("kr_income_2031*.yaml")] == ["kr_income_2031.yaml"]


def test_rollback_of_a_single_override_needs_no_effective_date(admin_env):
    _activate(_doc(effective_date="2031-01-01"))
    out = REGISTRY.invoke("sootool.policy_rollback", domain="tax", name="kr_income", year=2031)
    assert out["rolled_back"] is True
    assert not list(admin_env.glob("kr_income_2031*.yaml"))


def test_policy_get_and_export_honor_as_of(admin_env):
    _activate(_doc(effective_date="2031-01-01", effective_to="2031-06-30", rate="0.10"))
    _activate(_doc(effective_date="2031-07-01", rate="0.20"))
    early = REGISTRY.invoke("sootool.policy_get", domain="tax", name="kr_income", year=2031, as_of="2031-02-01")
    assert early["policy_version"]["effective_date"] == "2031-01-01"
    bundle = REGISTRY.invoke("sootool.policy_export", domain="tax", name="kr_income", year=2031,
                             as_of="2031-02-01")["bundle"]
    assert 'effective_date: "2031-01-01"' in bundle["yaml_content"]


def test_policy_list_shows_every_version_with_status(admin_env):
    _activate(_doc(effective_date="2031-01-01", effective_to="2031-06-30", rate="0.10"))
    _activate(_doc(effective_date="2031-07-01", status="proposed", rate="0.40"))
    entries = [e for e in REGISTRY.invoke("sootool.policy_list")["policies"]
               if e["name"] == "kr_income" and e["year"] == 2031]
    assert [(e["effective_date"], e["status"]) for e in entries] == [
        ("2031-01-01", "enacted"), ("2031-07-01", "proposed"),
    ]
