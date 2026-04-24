"""
GitHub Actions CI green 게이트 확인 스크립트.

현재 HEAD SHA 기준으로 GitHub API를 조회하여 CI workflow가
성공 상태인지 검증한다. 릴리스 전 필수 실행.

작성자: 최진호
작성일: 2026-04-24
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

OWNER   = "JinHo-von-Choi"
REPO    = "SooTool"
CI_NAME = "CI"

# GitHub API 베이스 URL — https 스킴 전용, file: 허용 없음
_GITHUB_API_BASE = "https://api.github.com"

# 지수 백오프 재시도 설정
RETRY_DELAYS: list[float] = [1.0, 4.0]


def _get_head_sha() -> str:
    """현재 git HEAD SHA를 반환한다."""
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _parse_oauth_token_from_hosts_yml(path: Path) -> str | None:
    """
    gh CLI hosts.yml 파일에서 oauth_token 값을 파싱하여 반환한다.

    stdlib만 사용하여 YAML 전체 파싱 없이 정규식으로 첫 매치를 추출한다.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    pattern = re.compile(r"^\s*oauth_token:\s*(\S+)", re.MULTILINE)
    match   = pattern.search(content)
    return match.group(1) if match else None


def _resolve_token() -> str | None:
    """
    토큰 해석 우선순위:
    1. GH_TOKEN 환경변수
    2. GITHUB_TOKEN 환경변수
    3. ~/.config/gh/hosts.yml oauth_token
    4. ~/snap/gh/current/.config/gh/hosts.yml oauth_token
    """
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    candidates: list[Path] = [
        Path.home() / ".config" / "gh" / "hosts.yml",
        Path.home() / "snap" / "gh" / "current" / ".config" / "gh" / "hosts.yml",
    ]
    for path in candidates:
        token = _parse_oauth_token_from_hosts_yml(path)
        if token:
            return token

    return None


def _build_request(url: str, token: str | None) -> urllib.request.Request:
    """GitHub API 요청 객체를 구성한다. https 스킴만 허용."""
    if not url.startswith("https://"):
        raise ValueError(f"안전하지 않은 URL 스킴: {url}")
    headers: dict[str, str] = {
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent":           f"{OWNER}/{REPO}-release-preflight",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)  # noqa: S310


def _fetch_with_retry(url: str, token: str | None) -> dict[str, Any]:
    """
    GitHub API를 호출하고 응답을 dict로 반환한다.

    HTTP 403(rate-limit) 및 5xx는 지수 백오프 2회 재시도.
    여전히 실패하면 exit 3.
    """
    last_exc: Exception | None = None

    for attempt, delay in enumerate([-1.0] + RETRY_DELAYS):
        if delay >= 0:
            time.sleep(delay)

        try:
            req = _build_request(url, token)
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (403,) or exc.code >= 500:
                print(
                    f"HTTP {exc.code} (attempt {attempt + 1}), 재시도 예정…",
                    file=sys.stderr,
                )
                continue
            # 4xx(403 제외)는 즉시 실패
            print(f"GitHub API 오류: HTTP {exc.code} {exc.reason}", file=sys.stderr)
            sys.exit(3)
        except urllib.error.URLError as exc:
            last_exc = exc
            print(f"네트워크 오류 (attempt {attempt + 1}): {exc.reason}", file=sys.stderr)
            continue

    print(f"GitHub API 호출 최종 실패: {last_exc}", file=sys.stderr)
    sys.exit(3)


def _find_ci_run(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """workflow_runs 목록에서 name == CI_NAME인 항목을 반환한다."""
    for run in runs:
        if run.get("name") == CI_NAME:
            return run
    return None


def main() -> None:
    """릴리스 CI 게이트 진입점."""
    sha   = _get_head_sha()
    token = _resolve_token()

    if token is None:
        print(
            "경고: GitHub 토큰을 찾을 수 없습니다. "
            "GH_TOKEN / GITHUB_TOKEN 환경변수 또는 "
            "~/.config/gh/hosts.yml을 확인하세요.",
            file=sys.stderr,
        )
        sys.exit(2)

    url = (
        f"{_GITHUB_API_BASE}/repos/{OWNER}/{REPO}/actions/runs"
        f"?head_sha={sha}&status=completed&per_page=50"
    )
    data: dict[str, Any] = _fetch_with_retry(url, token)
    runs: list[dict[str, Any]] = data.get("workflow_runs", [])

    ci_run = _find_ci_run(runs)

    if ci_run is None:
        print(
            f"SHA {sha}에 대한 완료된 CI 런을 찾을 수 없습니다. "
            "CI가 아직 실행 중이거나 해당 SHA에 대한 런이 없습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    conclusion: str = ci_run.get("conclusion", "")
    html_url:   str = ci_run.get("html_url", "(URL 없음)")

    if conclusion != "success":
        print(
            f"CI 런이 성공 상태가 아닙니다.\n"
            f"  conclusion : {conclusion}\n"
            f"  URL        : {html_url}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"CI run success: {html_url}")
    sys.exit(0)


if __name__ == "__main__":
    main()
