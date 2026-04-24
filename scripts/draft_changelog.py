"""
CHANGELOG [Unreleased] 섹션 초안 자동 생성.

git log에서 Conventional Commits를 파싱하여 섹션별로 분류한 Markdown을
stdout에 출력하거나 CHANGELOG.md에 in-place 삽입한다.

Usage:
    uv run python scripts/draft_changelog.py
    uv run python scripts/draft_changelog.py --since v0.1.1
    uv run python scripts/draft_changelog.py --since v0.1.1 --until HEAD
    uv run python scripts/draft_changelog.py --since v0.1.1 --write

작성자: 최진호
작성일: 2026-04-24
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
CHANGELOG_PATH: Path = REPO_ROOT / "CHANGELOG.md"

# Conventional Commits 파싱 정규식
CC_RE = re.compile(
    r"^(feat|fix|chore|docs|refactor|perf|test|build|ci|style|security)"
    r"(?:\(([^)]+)\))?(!?):\s*(.*)$"
)

# 타입 → 섹션 매핑 (scope 우선 처리는 별도 함수에서)
_TYPE_TO_SECTION: dict[str, str] = {
    "feat":     "Added",
    "fix":      "Fixed",
    "security": "Security",
    "test":     "Changed",
    "refactor": "Changed",
    "perf":     "Changed",
    "docs":     "Changed",
    "chore":    "Changed",
    "build":    "Changed",
    "ci":       "Changed",
    "style":    "Changed",
}

SECTION_ORDER: list[str] = [
    "Added",
    "Changed",
    "Fixed",
    "Security",
    "Unclassified",
]


def _latest_tag() -> str:
    """직전 태그를 반환한다. 실패 시 빈 문자열."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_log(since: str, until: str) -> list[tuple[str, str, str]]:
    """
    (hash, subject, body) 튜플 목록을 반환한다.

    커밋 구분자로 %x1f(Unit Separator)를 사용하여 본문 줄바꿈과 구분한다.
    """
    result = subprocess.run(
        [
            "git", "log",
            "--format=%H%x09%s%x09%b%x1f",
            f"{since}..{until}",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(
            f"ERROR: git log 실패: {result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(1)

    commits: list[tuple[str, str, str]] = []
    for raw in result.stdout.split("\x1f"):
        stripped = raw.strip()
        if not stripped:
            continue
        parts = stripped.split("\t", 2)
        if len(parts) < 2:
            continue
        hash_val = parts[0].strip()
        subject  = parts[1].strip()
        body     = parts[2].strip() if len(parts) > 2 else ""
        commits.append((hash_val, subject, body))
    return commits


def _classify(
    commit_type: str,
    scope: str,
    breaking: str,
    body: str,
) -> str:
    """커밋을 섹션 이름으로 분류한다."""
    # BREAKING CHANGE 본문 또는 ! 접미사
    if breaking == "!" or "BREAKING CHANGE:" in body:
        return "Security"  # Breaking은 Security 아래로 (스펙 명시)

    # scope=security 또는 type=security
    if commit_type == "security" or scope == "security":
        return "Security"

    # chore(security) 처리 포함
    if commit_type == "chore" and scope == "security":
        return "Security"

    return _TYPE_TO_SECTION.get(commit_type, "Unclassified")


def _parse_commits(
    commits: list[tuple[str, str, str]],
) -> dict[str, list[tuple[str, str]]]:
    """
    섹션별 (short_hash, subject) 리스트 딕셔너리를 반환한다.
    """
    sections: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for full_hash, subject, body in commits:
        short = full_hash[:7]
        m = CC_RE.match(subject)
        if m:
            commit_type = m.group(1)
            scope       = m.group(2) or ""
            breaking    = m.group(3) or ""
            clean_subj  = m.group(4).strip()
            section = _classify(commit_type, scope, breaking, body)
        else:
            clean_subj = subject
            section    = "Unclassified"
        sections[section].append((short, clean_subj))
    return dict(sections)


def _load_snapshot() -> str:
    """count_tools.py --json 호출 결과로 snapshot 요약 1줄을 만든다."""
    count_script = REPO_ROOT / "scripts" / "count_tools.py"
    result = subprocess.run(
        ["uv", "run", "python", str(count_script), "--json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        return "Current master snapshot: (count_tools.py 호출 실패)"

    try:
        data          = json.loads(result.stdout)
        domains       = data["calculation_domains"]
        base_tools    = data["base_tools"]
        policy_tools  = data["policy_tools"]
    except (json.JSONDecodeError, KeyError) as exc:
        return f"Current master snapshot: (파싱 실패: {exc})"

    return (
        f"Current master snapshot: {domains} domains, "
        f"{base_tools} base tools, "
        f"{policy_tools} admin policy-management tools, "
        "5 transport modes."
    )


def _render_body(
    sections: dict[str, list[tuple[str, str]]],
    snapshot: str,
) -> str:
    """
    [Unreleased] 헤더를 포함한 전체 Markdown 블록을 반환한다.
    빈 섹션은 생략한다.
    """
    lines: list[str] = [
        "## [Unreleased]",
        "",
        snapshot,
        "",
    ]
    for section in SECTION_ORDER:
        entries = sections.get(section)
        if not entries:
            continue
        lines.append(f"### {section}")
        for short, subject in entries:
            lines.append(f"- {subject} ({short})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_changelog(body: str) -> None:
    """
    CHANGELOG.md의 ## [Unreleased] 헤더 다음부터 다음 ## [ 전까지를
    생성된 body로 교체한다.

    body는 ## [Unreleased] 헤더 줄을 포함한 전체 블록이다.
    """
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    header_idx: int | None = None
    next_section_idx: int | None = None

    for i, line in enumerate(lines):
        if line.startswith("## [Unreleased]"):
            header_idx = i
            continue
        if header_idx is not None and line.startswith("## ["):
            next_section_idx = i
            break

    if header_idx is None:
        print("ERROR: CHANGELOG.md에 ## [Unreleased] 헤더를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    # body에서 헤더 줄 이후 내용만 추출 (헤더는 기존 파일 것을 유지)
    body_lines_raw = body.splitlines(keepends=True)
    # body_lines_raw[0]는 "## [Unreleased]\n" — 기존 헤더로 대체되므로 제거
    replacement_content = "".join(body_lines_raw[1:])

    if next_section_idx is not None:
        new_lines = (
            lines[:header_idx + 1]
            + [replacement_content + "\n"]
            + lines[next_section_idx:]
        )
    else:
        new_lines = lines[:header_idx + 1] + [replacement_content]

    CHANGELOG_PATH.write_text("".join(new_lines), encoding="utf-8")
    print(f"CHANGELOG.md 업데이트 완료: {CHANGELOG_PATH}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CHANGELOG [Unreleased] 섹션 초안 자동 생성"
    )
    parser.add_argument(
        "--since",
        default="",
        help="시작 git ref (미지정 시 직전 태그 자동 감지)",
    )
    parser.add_argument(
        "--until",
        default="HEAD",
        help="종료 git ref (기본: HEAD)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="CHANGELOG.md [Unreleased] 섹션을 in-place 교체",
    )
    args = parser.parse_args()

    since = args.since
    if not since:
        since = _latest_tag()
        if not since:
            print(
                "ERROR: --since 인자가 필요합니다 (태그 자동 감지 실패).",
                file=sys.stderr,
            )
            sys.exit(1)

    commits  = _git_log(since, args.until)
    sections = _parse_commits(commits)
    snapshot = _load_snapshot()
    body     = _render_body(sections, snapshot)

    if args.write:
        _write_changelog(body)
    else:
        print(body, end="")


if __name__ == "__main__":
    main()
