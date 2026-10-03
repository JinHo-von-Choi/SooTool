"""신고 유형별 구간표(dict of list)를 가진 정책의 검증 시험.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sootool.policy_mgmt.validators import _extract_bracket_tables, validate_policy

_US_DIR = Path(__file__).resolve().parents[2] / "src" / "sootool" / "policies" / "tax_us"
_US_POLICIES = sorted(_US_DIR.glob("*.yaml"))


def _name(path: Path) -> str:
    return path.stem.rsplit("_", 1)[0]


@pytest.mark.parametrize("path", _US_POLICIES, ids=lambda p: p.name)
def test_packaged_us_policies_validate_without_errors(path):
    report = validate_policy(yaml_content=path.read_text(encoding="utf-8"), domain="tax_us", name=_name(path))
    errors = [f for f in report["findings"] if f["level"] == "error"]
    assert not errors, errors


def test_per_status_tables_are_extracted_by_label():
    data = {
        "brackets":      {"single": [{"upper": 10, "rate": 0.1}, {"upper": None, "rate": 0.2}], "note": "x"},
        "ltcg_brackets": {"single": [{"upper": None, "rate": 0.0}]},
    }
    tables = _extract_bracket_tables(data)
    assert set(tables) == {"brackets.single", "ltcg_brackets.single"}


def _doc_with(brackets: dict) -> str:
    return yaml.safe_dump({
        "sha256": "x", "effective_date": "2026-01-01", "notice_no": "n", "source_url": "u",
        "data": {"brackets": brackets},
    })


def test_non_increasing_uppers_in_a_status_table_are_reported():
    text = _doc_with({"single": [{"upper": 20, "rate": 0.1}, {"upper": 10, "rate": 0.2}, {"upper": None, "rate": 0.3}]})
    report = validate_policy(yaml_content=text, domain="tax_us", name="federal_income")
    assert any(f["path"].startswith("brackets.single") and "increasing" in f["message"] for f in report["findings"])


def test_non_mapping_bracket_entries_are_reported_not_raised():
    text = _doc_with({"single": ["12400", "50400"]})
    report = validate_policy(yaml_content=text, domain="tax_us", name="federal_income")
    assert any(f["path"] == "brackets.single" and f["level"] == "error" for f in report["findings"])
