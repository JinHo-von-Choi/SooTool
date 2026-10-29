"""ADR-019 단일 소스 가드: 배포 문서의 도구 수 선언이 레지스트리와 일치하는지 검사한다.

CI(.github/workflows/ci.yml)의 "Tool count single source guard" 단계만 거치던 검사를
pytest로도 옮겨, CI 가드 단계에 도달하지 않아도 드리프트가 pytest 단계에서 드러나게 한다.

2026-10-30 감사에서 CHANGELOG 의 base tools 수(275)가 실제(276)와 어긋난 채 2주간 방치
돼 있었다. CI 가드는 이 불일치를 정확히 잡아냈지만(Guard 가 실제로 작동했다), 그 단계가
Mypy 실패 뒤에 있어 실행되지 않았다. 이 테스트는 그 의존을 없앤다.

pytest 판정은 CI grep 보다 엄격하다. CI 는 CHANGELOG 전체에서 문자열을 찾지만, 여기서는
``[Unreleased]`` 절만 검사해 과거 릴리스 절의 숫자가 오탐을 만들지 않게 한다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]


def _load_registry_snapshot() -> dict[str, Any]:
    """scripts/count_tools.py 의 집계 로직을 그대로 재사용한다(단일 소스 유지)."""
    spec = importlib.util.spec_from_file_location(
        "sootool_count_tools_under_test", _ROOT / "scripts" / "count_tools.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    snapshot: dict[str, Any] = module._load_registry_snapshot()
    return snapshot


def _latest_registry_count_line() -> str:
    """CHANGELOG 에서 가장 위에 있는 REGISTRY 수치 선언 줄을 돌려준다.

    릴리스 절차를 거치면 내용이 ``[Unreleased]`` 에서 ``[x.y.z]`` 절로 옮겨 가므로,
    항상 "[Unreleased] 만 검사" 하면 릴리스 직후에 거짓 실패가 난다. 대신 가장 최근
    릴리스의 선언 줄을 검사한다.
    """
    text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if "REGISTRY 수치:" in ln]
    assert lines, "CHANGELOG.md 에서 REGISTRY 수치 선언을 찾지 못했다"
    return lines[0]


def test_changelog_unreleased_counts_match_the_registry() -> None:
    snapshot = _load_registry_snapshot()
    domains = snapshot["calculation_domains"]
    base    = snapshot["base_tools"]
    policy  = snapshot["policy_tools"]
    expected = f"{domains} domains, {base} base tools, {policy} admin policy-management tools"
    assert expected in _latest_registry_count_line(), (
        f"CHANGELOG.md 최신 REGISTRY 수치 선언 불일치: '{expected}' 를 찾지 못했다"
    )


def test_readme_first_paragraph_counts_match_the_registry() -> None:
    snapshot = _load_registry_snapshot()
    domains = snapshot["calculation_domains"]
    base    = snapshot["base_tools"]
    policy  = snapshot["policy_tools"]
    readme  = (_ROOT / "README.md").read_text(encoding="utf-8")
    expected = f"{domains}개 계산 도메인 {base}개 기본 도구 + {policy}개 admin 정책 도구"
    assert expected in readme, f"README 첫 문단 도구 수 불일치: '{expected}' 를 찾지 못했다"


def test_readme_catalog_header_counts_match_the_registry() -> None:
    snapshot = _load_registry_snapshot()
    domains = snapshot["calculation_domains"]
    base    = snapshot["base_tools"]
    policy  = snapshot["policy_tools"]
    readme  = (_ROOT / "README.md").read_text(encoding="utf-8")
    expected = f"({base}개 기본 + {policy}개 admin, {domains} 계산 도메인"
    assert expected in readme, f"README 카탈로그 헤더 도구 수 불일치: '{expected}' 를 찾지 못했다"


def test_pyproject_description_counts_match_the_registry() -> None:
    snapshot = _load_registry_snapshot()
    domains = snapshot["calculation_domains"]
    base    = snapshot["base_tools"]
    policy  = snapshot["policy_tools"]
    pyproject = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expected = f"{domains}개 계산 도메인 {base}개 기본 도구 + {policy}개 admin 정책 도구"
    assert expected in pyproject, f"pyproject.toml description 도구 수 불일치: '{expected}' 를 찾지 못했다"


def test_admin_gated_policy_tools_count_is_four() -> None:
    """admin 게이트가 걸린 정책 쓰기 도구는 4종(propose/activate/rollback/import)이다."""
    snapshot = _load_registry_snapshot()
    assert snapshot["admin_policy_tools"] == 4, snapshot["admin_tool_names"]
    assert snapshot["admin_tool_names"] == [
        "policy_activate",
        "policy_import",
        "policy_propose",
        "policy_rollback",
    ]
