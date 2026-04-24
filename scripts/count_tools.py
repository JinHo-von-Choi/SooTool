"""
SooTool 도구 카운트 집계 스크립트.

REGISTRY를 `_load_modules()`로 전수 적재한 뒤 네임스페이스별 집계,
전체 도구 수, 계산 도메인 수, 운영 도메인(core·sootool) 수,
정책 도구 및 admin-gated 정책 도구 수를 산출한다.

배포 문서(README·CHANGELOG·pyproject.toml)의 선언 숫자와 대조해
단일 소스(ADR-019)를 유지하기 위한 CI 가드로 사용한다.

Usage:
    uv run python scripts/count_tools.py            # 사람이 읽기
    uv run python scripts/count_tools.py --json     # 기계 파싱
    uv run python scripts/count_tools.py --assert-total 246
    uv run python scripts/count_tools.py --assert-domains 16
    uv run python scripts/count_tools.py --assert-admin 4
    uv run python scripts/count_tools.py --tests    # pytest collect 테스트 수도 병기
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from typing import Any

# 운영 네임스페이스(계산 도메인에서 제외)
OPERATIONAL_NAMESPACES: frozenset[str] = frozenset({"core", "sootool"})


def _load_registry_snapshot() -> dict[str, Any]:
    from sootool.policy_mgmt import tools as policy_tools
    from sootool.server import _load_modules

    _load_modules()
    from sootool.core.registry import REGISTRY

    entries = REGISTRY.list()

    namespace_counts: Counter[str] = Counter()
    for e in entries:
        namespace_counts[e.namespace] += 1

    # 정책 도구는 sootool 네임스페이스 내에서 'policy_' 접두어를 갖는다.
    policy_tool_entries = [
        e for e in entries if e.namespace == "sootool" and e.name.startswith("policy_")
    ]
    policy_tools_count = len(policy_tool_entries)

    # admin-gated 정책 도구: policy_mgmt.tools 모듈에서 _require_admin() 호출이
    # 존재하는 함수와 REGISTRY 등록 이름을 교차해 판정한다.
    admin_names = {
        "policy_propose",
        "policy_activate",
        "policy_rollback",
        "policy_import",
    }
    # 모듈 소스에서 admin 게이트를 실제 콜하는지 정적 검증 (방어 로직)
    src = policy_tools.__loader__.get_source(policy_tools.__name__)  # type: ignore[union-attr]
    verified_admin: set[str] = set()
    if src:
        lines = src.splitlines()
        current_def: str | None = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def ") and "(" in stripped:
                current_def = stripped[4 : stripped.index("(")]
            if current_def and "_require_admin()" in stripped and current_def in admin_names:
                verified_admin.add(current_def)
    admin_tools_count = len(verified_admin)

    calculation_namespaces = sorted(
        ns for ns in namespace_counts if ns not in OPERATIONAL_NAMESPACES
    )
    operational_namespaces = sorted(
        ns for ns in namespace_counts if ns in OPERATIONAL_NAMESPACES
    )

    total = sum(namespace_counts.values())

    return {
        "total_tools":               total,
        "total_namespaces":          len(namespace_counts),
        "calculation_domains":       len(calculation_namespaces),
        "operational_namespaces":    len(operational_namespaces),
        "policy_tools":              policy_tools_count,
        "admin_policy_tools":        admin_tools_count,
        "base_tools":                total - policy_tools_count,
        "namespaces":                dict(sorted(namespace_counts.items())),
        "calculation_namespace_list": calculation_namespaces,
        "operational_namespace_list": operational_namespaces,
        "admin_tool_names":          sorted(verified_admin),
    }


def _collect_pytest_count() -> int | None:
    """pytest --collect-only -q 로 테스트 수를 집계 (옵션 모드)."""
    try:
        proc = subprocess.run(  # noqa: S603
            ["uv", "run", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    # 마지막 줄 "N tests collected" 패턴 파싱
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.endswith("tests collected") or line.endswith("test collected"):
            try:
                return int(line.split()[0])
            except (ValueError, IndexError):
                return None
    return None


def _print_human(snapshot: dict[str, Any], test_count: int | None) -> None:
    print(f"총 도구 수: {snapshot['total_tools']}")
    print(f"총 네임스페이스: {snapshot['total_namespaces']}")
    print(
        f"계산 도메인: {snapshot['calculation_domains']} "
        f"(운영 제외: {', '.join(snapshot['operational_namespace_list'])})"
    )
    print(f"정책 도구: {snapshot['policy_tools']}")
    print(
        f"admin-gated 정책 도구: {snapshot['admin_policy_tools']} "
        f"({', '.join(snapshot['admin_tool_names'])})"
    )
    print(f"기본 도구(= 전체 - policy): {snapshot['base_tools']}")
    if test_count is not None:
        print(f"pytest 수집 테스트: {test_count}")
    print("\n네임스페이스별 도구 수:")
    for ns, count in snapshot["namespaces"].items():
        marker = "  (operational)" if ns in OPERATIONAL_NAMESPACES else ""
        print(f"  {ns:15s} {count}{marker}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SooTool 도구 카운트 집계")
    parser.add_argument("--json", action="store_true", help="JSON 포맷 출력")
    parser.add_argument("--assert-total", type=int, help="전체 도구 수 단언")
    parser.add_argument("--assert-domains", type=int, help="계산 도메인 수 단언")
    parser.add_argument("--assert-admin", type=int, help="admin 정책 도구 수 단언")
    parser.add_argument("--assert-policy", type=int, help="정책 도구 수 단언")
    parser.add_argument("--assert-base", type=int, help="base 도구 수 단언 (total - policy_tools)")
    parser.add_argument(
        "--assert-namespaces",
        type=str,
        default=None,
        help='네임스페이스별 도구 수 JSON 단언 예: \'{"finance":15,"tax":10}\'',
    )
    parser.add_argument(
        "--tests",
        action="store_true",
        help="pytest --collect-only 로 테스트 수도 집계",
    )
    args = parser.parse_args(argv)

    snapshot = _load_registry_snapshot()
    test_count = _collect_pytest_count() if args.tests else None
    if test_count is not None:
        snapshot["pytest_tests"] = test_count

    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_human(snapshot, test_count)

    # assertion gates
    failures: list[str] = []
    if args.assert_total is not None and snapshot["total_tools"] != args.assert_total:
        failures.append(
            f"total_tools={snapshot['total_tools']} != expected {args.assert_total}"
        )
    if (
        args.assert_domains is not None
        and snapshot["calculation_domains"] != args.assert_domains
    ):
        failures.append(
            f"calculation_domains={snapshot['calculation_domains']} "
            f"!= expected {args.assert_domains}"
        )
    if (
        args.assert_admin is not None
        and snapshot["admin_policy_tools"] != args.assert_admin
    ):
        failures.append(
            f"admin_policy_tools={snapshot['admin_policy_tools']} "
            f"!= expected {args.assert_admin}"
        )
    if (
        args.assert_policy is not None
        and snapshot["policy_tools"] != args.assert_policy
    ):
        failures.append(
            f"policy_tools={snapshot['policy_tools']} "
            f"!= expected {args.assert_policy}"
        )
    if args.assert_base is not None and snapshot["base_tools"] != args.assert_base:
        failures.append(
            f"base_tools={snapshot['base_tools']} != expected {args.assert_base}"
        )
    if args.assert_namespaces is not None:
        try:
            expected = json.loads(args.assert_namespaces)
        except json.JSONDecodeError as e:
            failures.append(f"--assert-namespaces JSON parse error: {e}")
        else:
            for ns, exp_count in expected.items():
                actual = snapshot["namespaces"].get(ns)
                if actual != exp_count:
                    failures.append(
                        f"namespace[{ns}]={actual} != expected {exp_count}"
                    )

    if failures:
        print("\nassertion 실패:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
