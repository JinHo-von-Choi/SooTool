from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "policy_stamp.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(_SCRIPT), *args], capture_output=True, text=True, check=False, timeout=60,
    )


def test_packaged_policies_have_matching_hashes():
    result = _run("--check")
    assert result.returncode == 0, result.stdout


def test_stamp_repairs_a_modified_policy_and_check_detects_the_mismatch(tmp_path):
    policy = tmp_path / "kr_income_2099.yaml"
    policy.write_text('sha256: "x"\neffective_date: "2099-01-01"\ndata:\n  brackets: []\n', encoding="utf-8")
    assert _run("--check", str(policy)).returncode == 1
    assert _run(str(policy)).returncode == 0
    assert _run("--check", str(policy)).returncode == 0
    policy.write_text(policy.read_text(encoding="utf-8").replace("2099", "2098"), encoding="utf-8")
    assert _run("--check", str(policy)).returncode == 1


def test_stamp_adds_a_missing_declaration(tmp_path):
    policy = tmp_path / "p_2099.yaml"
    policy.write_text('effective_date: "2099-01-01"\n', encoding="utf-8")
    _run(str(policy))
    assert policy.read_text(encoding="utf-8").startswith('sha256: "')
