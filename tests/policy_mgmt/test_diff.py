"""Tests for semantic policy diff.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from sootool.policy_mgmt.diff import diff_policies, diff_policy_data


def test_no_changes() -> None:
    data = {
        "brackets": [
            {"upper": "14000000", "rate": "0.06"},
            {"upper": None, "rate": "0.15"},
        ]
    }
    result = diff_policy_data(data, data, 2025, 2026)
    assert result["changes"] == []


def test_rate_changed() -> None:
    old_data = {
        "brackets": [
            {"upper": "14000000", "rate": "0.06"},
            {"upper": None, "rate": "0.15"},
        ]
    }
    new_data = {
        "brackets": [
            {"upper": "14000000", "rate": "0.08"},  # changed
            {"upper": None, "rate": "0.15"},
        ]
    }
    result = diff_policy_data(old_data, new_data, 2025, 2026)
    assert len(result["changes"]) == 1
    change = result["changes"][0]
    assert change["type"] == "rate_changed"
    assert change["old_rate"] == "0.06"
    assert change["new_rate"] == "0.08"


def test_bracket_added() -> None:
    old_data = {
        "brackets": [{"upper": None, "rate": "0.06"}]
    }
    new_data = {
        "brackets": [
            {"upper": "14000000", "rate": "0.06"},
            {"upper": None, "rate": "0.15"},
        ]
    }
    result = diff_policy_data(old_data, new_data, 2025, 2026)
    types = {c["type"] for c in result["changes"]}
    assert "added" in types


def test_bracket_removed() -> None:
    old_data = {
        "brackets": [
            {"upper": "14000000", "rate": "0.06"},
            {"upper": None, "rate": "0.15"},
        ]
    }
    new_data = {
        "brackets": [{"upper": None, "rate": "0.15"}]
    }
    result = diff_policy_data(old_data, new_data, 2025, 2026)
    types = {c["type"] for c in result["changes"]}
    assert "removed" in types


def test_dsr_field_changed() -> None:
    old_data = {"dsr_cap": "0.40", "ltv": {}, "dti": {}}
    new_data = {"dsr_cap": "0.45", "ltv": {}, "dti": {}}
    result = diff_policy_data(old_data, new_data, 2025, 2026)
    fields = {c.get("field") for c in result["changes"]}
    assert "dsr_cap" in fields


def test_diff_policies_wrapper() -> None:
    old_doc = {"data": {"brackets": [{"upper": None, "rate": "0.06"}]}}
    new_doc = {"data": {"brackets": [{"upper": None, "rate": "0.07"}]}}
    result = diff_policies(old_doc, new_doc, 2025, 2026)
    assert result["changes"][0]["type"] == "rate_changed"
