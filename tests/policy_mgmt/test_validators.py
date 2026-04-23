"""Tests for the 6-stage validation pipeline.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

import hashlib
import re

from sootool.policy_mgmt.validators import validate_policy


def _make_yaml(sha_override: str | None = None, year: int = 2027) -> str:
    body = (
        f'sha256: "PLACEHOLDER"\n'
        f'effective_date: "{year}-01-01"\n'
        f'notice_no: "test-{year}"\n'
        f'source_url: "https://example.com"\n'
        f'data:\n'
        f'  brackets:\n'
        f'    - upper: 14000000\n'
        f'      rate: 0.06\n'
        f'    - upper: null\n'
        f'      rate: 0.15\n'
    )
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    if sha_override:
        return body.replace("PLACEHOLDER", sha_override)
    return body.replace("PLACEHOLDER", real_hash)


def test_stage1_invalid_yaml() -> None:
    report = validate_policy("{ bad: yaml: : :", domain="tax")
    assert report["status"] == "error"
    stages = [f["stage"] for f in report["findings"]]
    assert 1 in stages


def test_stage2_missing_required_field() -> None:
    yaml_no_sha = (
        'effective_date: "2027-01-01"\n'
        'notice_no: "test"\n'
        'source_url: "https://example.com"\n'
        'data:\n'
        '  brackets: []\n'
    )
    report = validate_policy(yaml_no_sha, domain="tax")
    assert report["status"] == "error"
    assert any(f["path"] == "sha256" for f in report["findings"])


def test_stage3_schema_validation_error() -> None:
    # brackets has non-None upper on last bracket — schema error
    import hashlib
    body = (
        'sha256: "PLACEHOLDER"\n'
        'effective_date: "2027-01-01"\n'
        'notice_no: "test"\n'
        'source_url: "https://example.com"\n'
        'data:\n'
        '  brackets:\n'
        '    - upper: 14000000\n'
        '      rate: 0.06\n'
        '    - upper: 50000000\n'  # last should be null
        '      rate: 0.15\n'
    )
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    yaml_content = body.replace("PLACEHOLDER", real_hash)
    report = validate_policy(yaml_content, domain="tax", name="kr_income")
    assert report["status"] == "error"


def test_stage4_brackets_not_monotone() -> None:
    import hashlib
    body = (
        'sha256: "PLACEHOLDER"\n'
        'effective_date: "2027-01-01"\n'
        'notice_no: "test"\n'
        'source_url: "https://example.com"\n'
        'data:\n'
        '  brackets:\n'
        '    - upper: 50000000\n'
        '      rate: 0.15\n'
        '    - upper: 14000000\n'  # not monotone
        '      rate: 0.06\n'
        '    - upper: null\n'
        '      rate: 0.35\n'
    )
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    yaml_content = body.replace("PLACEHOLDER", real_hash)
    report = validate_policy(yaml_content, domain="tax")
    assert report["status"] == "error"


def test_stage5_sensitivity_warning() -> None:
    yaml_content = _make_yaml(year=2027)
    # Force a big change by providing dramatically different previous rates
    prev_big = {
        "brackets": [
            {"upper": 14000000, "rate": "0.99"},  # old rate was 0.99, new is 0.06 → delta 0.93 > 0.5
            {"upper": None, "rate": "0.15"},
        ]
    }
    report = validate_policy(yaml_content, domain="tax", prev_year_data=prev_big, sensitivity_threshold=0.5)
    warning_stages = [f for f in report["findings"] if f["stage"] == 5]
    assert len(warning_stages) > 0


def test_stage6_sha256_mismatch() -> None:
    yaml_bad_sha = _make_yaml(sha_override="deadbeefdeadbeef" * 4)
    report = validate_policy(yaml_bad_sha, domain="tax")
    assert report["status"] == "error"
    assert any(f["path"] == "sha256" for f in report["findings"])


def test_stage6_auto_fix_sha256() -> None:
    yaml_bad_sha = _make_yaml(sha_override="deadbeefdeadbeef" * 4)
    report = validate_policy(yaml_bad_sha, domain="tax", auto_fix_sha256=True)
    # With auto_fix, sha256 mismatch becomes info
    sha_findings = [f for f in report["findings"] if f["path"] == "sha256"]
    levels = {f["level"] for f in sha_findings}
    assert "error" not in levels


def test_valid_policy_ok() -> None:
    yaml_content = _make_yaml()
    report = validate_policy(yaml_content, domain="tax", name="kr_income")
    assert report["status"] == "ok"
    assert report["sha256"] != ""
