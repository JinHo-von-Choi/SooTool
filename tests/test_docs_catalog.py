"""문서의 도구 목록과 수치가 레지스트리와 어긋나지 않는지 검사한다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from sootool import server
from sootool.core.registry import REGISTRY

_ROOT = Path(__file__).resolve().parents[1]


def test_generated_tool_catalog_is_current():
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(_ROOT / "scripts" / "gen_tool_catalog.py"), "--check"],
        check=False, capture_output=True, text=True, cwd=_ROOT,
    )
    assert result.returncode == 0, result.stdout


def test_readme_catalog_counts_match_the_registry():
    server._load_modules()
    actual = Counter(e.namespace for e in REGISTRY.list())
    rows = re.findall(r"^\|([a-z_]+)\|(\d+)\|", (_ROOT / "README.md").read_text(encoding="utf-8"), re.MULTILINE)
    assert rows, "README 카탈로그 표를 찾지 못했다"
    wrong = {ns: (int(count), actual[ns]) for ns, count in rows if ns in actual and int(count) != actual[ns]}
    assert not wrong, f"README 표의 도구 수가 레지스트리와 다르다(표, 실제): {wrong}"
    assert {ns for ns, _ in rows} >= set(actual) - {"sootool"}
