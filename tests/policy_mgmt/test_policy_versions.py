"""정책 버전 해석: 시행 기간, as_of, 개정안(proposed) 처리."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sootool import server
from sootool.core.errors import (
    InvalidInputError,
    PolicyFormatError,
    PolicyNotEnactedError,
    PolicyNotInEffectError,
)
from sootool.core.policy_context import policy_context
from sootool.core.registry import REGISTRY
from sootool.policies import _compute_sha256
from sootool.policy_mgmt import loader


def _write_policy(
    directory: Path,
    filename:  str,
    *,
    effective_date: str,
    rate:           str,
    status:         str | None = None,
    effective_to:   str | None = None,
    citations:      bool = True,
) -> None:
    lines = [f'effective_date: "{effective_date}"']
    if effective_to:
        lines.append(f'effective_to: "{effective_to}"')
    if status:
        lines.append(f"status: {status}")
    lines += [
        'notice_no: "시험용 소득세법 제55조"',
        'source_url: "https://example.invalid/law"',
    ]
    if citations:
        lines += ["citations:", '  - law: "소득세법"', '    article: "제55조"']
    lines += ["data:", "  brackets:", "    - upper: null", f"      rate: {rate}"]
    body = "\n".join(lines) + "\n"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(f'sha256: "{_compute_sha256(body)}"\n{body}', encoding="utf-8")


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    server._load_modules()
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path))
    loader.invalidate_cache()
    yield tmp_path / "tax"
    loader.invalidate_cache()


def _rate(as_of: str | None = None, *, include_proposed: bool = False, year: int = 2030) -> str:
    ctx = policy_context(as_of=date.fromisoformat(as_of) if as_of else None, include_proposed=include_proposed)
    with ctx:
        return str(loader.load("tax", "kr_income", year)["data"]["brackets"][0]["rate"])


# --- 기본 선택 ---

def test_single_version_loads_with_enacted_status_and_open_period(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", rate="0.10")
    pv = loader.load("tax", "kr_income", 2030)["policy_version"]
    assert pv["status"] == "enacted"
    assert pv["effective_date"] == "2030-01-01"
    assert pv["effective_to"] is None
    assert pv["citations"] == [{"law": "소득세법", "article": "제55조"}]


def test_without_as_of_the_latest_enacted_version_wins_regardless_of_today(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", effective_to="2030-06-30",
                  rate="0.10", status="superseded")
    _write_policy(store, "kr_income_2030@2030-07-01.yaml", effective_date="2030-07-01", rate="0.20")
    assert _rate() == "0.2"


# --- 시점 지정 ---

@pytest.fixture
def two_versions(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", effective_to="2030-06-30",
                  rate="0.10", status="superseded")
    _write_policy(store, "kr_income_2030@2030-07-01.yaml", effective_date="2030-07-01", rate="0.20")
    return store


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2030-01-01", "0.1"),
        ("2030-03-15", "0.1"),
        ("2030-06-30", "0.1"),
        ("2030-07-01", "0.2"),
        ("2030-12-31", "0.2"),
    ],
)
def test_as_of_selects_the_version_in_effect_on_that_day(two_versions, as_of, expected):
    assert _rate(as_of) == expected


def test_as_of_before_the_first_version_raises_with_available_periods(two_versions):
    with pytest.raises(PolicyNotInEffectError) as info:
        _rate("2029-12-31")
    periods = info.value.details()["periods"]
    assert [p["effective_from"] for p in periods] == ["2030-01-01", "2030-07-01"]
    assert info.value.to_payload()["code"] == "policy_not_in_effect"


def test_as_of_after_a_closed_period_without_successor_raises(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", effective_to="2030-03-31", rate="0.10")
    with pytest.raises(PolicyNotInEffectError):
        _rate("2030-04-01")


def test_superseded_version_is_not_the_default_but_serves_its_own_period(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", effective_to="2030-06-30",
                  rate="0.10", status="superseded")
    assert _rate("2030-02-01") == "0.1"
    with pytest.raises(Exception) as info:
        _rate()
    assert info.value.to_payload()["code"] in {"policy_unavailable"}


# --- 개정안 ---

def test_proposed_policy_is_hidden_unless_explicitly_included(store):
    _write_policy(store, "kr_income_2031.yaml", effective_date="2031-01-01", rate="0.30", status="proposed")
    with pytest.raises(PolicyNotEnactedError) as info:
        _rate(year=2031)
    assert "include_proposed" in str(info.value)
    assert info.value.to_payload()["code"] == "policy_not_enacted"


def test_include_proposed_loads_the_draft_and_reports_its_status(store):
    _write_policy(store, "kr_income_2031.yaml", effective_date="2031-01-01", rate="0.30", status="proposed")
    with policy_context(as_of=None, include_proposed=True):
        pv = loader.load("tax", "kr_income", 2031)["policy_version"]
    assert pv["status"] == "proposed"


def test_proposed_version_never_replaces_an_enacted_one_unless_included(store):
    _write_policy(store, "kr_income_2032.yaml", effective_date="2032-01-01", rate="0.10")
    _write_policy(store, "kr_income_2032@2032-07-01.yaml", effective_date="2032-07-01", rate="0.40", status="proposed")
    assert _rate(year=2032) == "0.1"
    assert _rate("2032-08-01", year=2032) == "0.1"
    assert _rate("2032-08-01", include_proposed=True, year=2032) == "0.4"


def test_as_of_inside_a_proposed_only_period_reports_not_enacted(store):
    _write_policy(store, "kr_income_2031.yaml", effective_date="2031-01-01", rate="0.30", status="proposed")
    with pytest.raises(PolicyNotEnactedError):
        _rate("2031-06-01", year=2031)


# --- 저장소 우선순위와 형식 검증 ---

def test_override_file_replaces_the_package_file_of_the_same_name(tmp_path, monkeypatch):
    server._load_modules()
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path))
    loader.invalidate_cache()
    _write_policy(tmp_path / "tax", "kr_income_2026.yaml", effective_date="2026-01-01", rate="0.99")
    pv = loader.load("tax", "kr_income", 2026)
    assert pv["source"] == "override"
    assert pv["data"]["brackets"][0]["rate"] == 0.99
    loader.invalidate_cache()


def test_invalid_status_is_a_typed_format_error(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", rate="0.10", status="draft")
    with pytest.raises(PolicyFormatError):
        loader.load("tax", "kr_income", 2030)


def test_effective_to_before_effective_date_is_rejected(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-06-01", effective_to="2030-01-01", rate="0.1")
    with pytest.raises(PolicyFormatError):
        loader.load("tax", "kr_income", 2030)


def test_list_available_policies_reports_every_version_with_status(store):
    _write_policy(store, "kr_income_2030.yaml", effective_date="2030-01-01", effective_to="2030-06-30",
                  rate="0.10", status="superseded")
    _write_policy(store, "kr_income_2030@2030-07-01.yaml", effective_date="2030-07-01", rate="0.20")
    mine = [e for e in loader.list_available_policies() if e["name"] == "kr_income" and e["year"] == 2030]
    assert [(e["effective_date"], e["status"], e["effective_to"]) for e in mine] == [
        ("2030-01-01", "superseded", "2030-06-30"),
        ("2030-07-01", "enacted", None),
    ]


# --- 도구 호출 수준 (as_of, include_proposed 인자) ---

def _income(**kwargs):
    return REGISTRY.invoke("tax.kr_income", taxable_income="10000000", year=2030, **kwargs)


def test_tool_accepts_as_of_and_reports_the_version_used(two_versions):
    early = _income(as_of="2030-03-01")
    late  = _income(as_of="2030-09-01")
    assert early["tax"] == "1000000"
    assert late["tax"] == "2000000"
    assert early["policy_effective_date"] == "2030-01-01"
    assert early["policy_effective_to"] == "2030-06-30"
    assert late["policy_status"] == "enacted"
    assert late["policy_citations"] == [{"law": "소득세법", "article": "제55조"}]


def test_policy_arguments_are_part_of_the_integrity_input_hash(two_versions):
    plain = _income()["_meta"]["integrity"]["input_hash"]
    early = _income(as_of="2030-03-01")["_meta"]["integrity"]["input_hash"]
    late  = _income(as_of="2030-09-01")["_meta"]["integrity"]["input_hash"]
    assert len({plain, early, late}) == 3
    assert plain == _income(as_of=None, include_proposed=False)["_meta"]["integrity"]["input_hash"]


def test_receipt_carries_policy_period_and_status(two_versions):
    stamp = _income(as_of="2030-03-01")["_meta"]["integrity"]
    assert stamp["policy_status"] == "superseded"
    assert stamp["policy_effective_from"] == "2030-01-01"
    assert stamp["policy_effective_to"] == "2030-06-30"


def test_proposed_result_is_labelled_and_hinted(store):
    _write_policy(store, "kr_income_2031.yaml", effective_date="2031-01-01", rate="0.30", status="proposed")
    result = REGISTRY.invoke(
        "tax.kr_income", taxable_income="10000000", year=2031, include_proposed=True,
    )
    assert result["policy_status"] == "proposed"
    assert result["_meta"]["integrity"]["policy_status"] == "proposed"
    assert "proposed_policy_in_use" in {h["signal"] for h in result["_meta"]["hints"]}
    with pytest.raises(PolicyNotEnactedError):
        REGISTRY.invoke("tax.kr_income", taxable_income="10000000", year=2031)


def test_invalid_policy_arguments_are_typed_errors(two_versions):
    with pytest.raises(InvalidInputError):
        _income(as_of="2030/03/01")
    with pytest.raises(InvalidInputError):
        _income(as_of=20300301)
    with pytest.raises(InvalidInputError):
        _income(include_proposed="yes")


def test_policy_context_does_not_leak_after_the_call(two_versions):
    from sootool.core.policy_context import POLICY_AS_OF, POLICY_INCLUDE_PROPOSED

    _income(as_of="2030-03-01", include_proposed=True)
    assert POLICY_AS_OF.get() is None
    assert POLICY_INCLUDE_PROPOSED.get() is False


def test_batch_items_carry_their_own_as_of(two_versions):
    out = REGISTRY.invoke("core.batch", items=[
        {"id": "a", "tool": "tax.kr_income",
         "args": {"taxable_income": "10000000", "year": 2030, "as_of": "2030-03-01"}},
        {"id": "b", "tool": "tax.kr_income",
         "args": {"taxable_income": "10000000", "year": 2030, "as_of": "2030-09-01"}},
    ])
    taxes = {r["id"]: r["result"]["tax"] for r in out["results"]}
    assert taxes == {"a": "1000000", "b": "2000000"}


def test_policy_context_is_inherited_by_tools_that_delegate_to_other_tools():
    """위임 도구(양도소득세 부동산 래퍼, 시급 -> 월급)가 하위 도구의 정책 로드에도 as_of 를 적용한다."""
    server._load_modules()
    loader.invalidate_cache()
    sale = {"acquisition_price": "500000000", "sale_price": "800000000", "holding_years": 3,
            "is_one_house": False, "year": 2026}
    ok = REGISTRY.invoke("realestate.kr_transfer_tax", as_of="2026-06-01", **sale)
    assert ok["policy_effective_date"] == "2026-01-01"
    with pytest.raises(PolicyNotInEffectError):
        REGISTRY.invoke("realestate.kr_transfer_tax", as_of="2025-06-01", **sale)

    wage = {"hourly_wage": "12000", "year": 2026}
    assert REGISTRY.invoke("payroll.hourly_to_monthly_net", as_of="2026-06-01", **wage)["_meta"]["integrity"]
    with pytest.raises(PolicyNotInEffectError):
        REGISTRY.invoke("payroll.hourly_to_monthly_net", as_of="2025-06-01", **wage)


def test_verify_receipt_replays_with_as_of(two_versions):
    args    = {"taxable_income": "10000000", "year": 2030, "as_of": "2030-03-01"}
    receipt = REGISTRY.invoke("tax.kr_income", **args)["_meta"]["integrity"]
    ok      = REGISTRY.invoke("sootool.verify_receipt", tool="tax.kr_income", arguments=args, receipt=receipt)
    assert ok["valid"] is True
    other   = REGISTRY.invoke(
        "sootool.verify_receipt", tool="tax.kr_income",
        arguments={**args, "as_of": "2030-09-01"}, receipt=receipt,
    )
    assert other["valid"] is False
    assert "input_hash" in other["mismatches"]
    assert "policy_sha256" in other["mismatches"]
