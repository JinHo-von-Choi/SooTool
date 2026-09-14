# SooTool 프로젝트 평가 및 개선 요구사항

작성자: 최진호
작성일: 2026-04-24

## 평가 범위

- Python 3.12 기반 SooTool MCP 서버의 아키텍처, 테스트, CI, 보안 경계, 운영 준비도를 평가한다.
- README, `pyproject.toml`, ADR 문서, GitHub Actions, 핵심 런타임 모듈, 테스트 스위트를 검토 대상으로 삼는다.
- 검증 명령은 `uv run pytest -q`, `uv run ruff check src/sootool tests scripts`, `uv run mypy src/sootool scripts`, `uv build`, `uv run python scripts/mcp_smoke_test.py`를 기준으로 한다.

## 필수 개선 요구사항

- CI 도구 수 가드는 README 첫 문단과 CHANGELOG의 선언 문자열을 현재 레지스트리 집계값과 일치시켜 통과시켜야 한다.
- `scripts/count_tools.py`의 `base_tools` 의미는 문서와 CI 계산식 중 하나로 통일해야 한다. 현재 JSON 출력은 전체 도구 264개, 정책 도구 10개, admin-gated 정책 도구 4개에서 `base_tools=260`으로 표시하지만 CI는 `total_tools - policy_tools = 254`를 기본 도구 수로 사용한다.
- `core.pipeline`은 `step_timeout_s`와 `pipeline_timeout_s` 필드를 선언한 만큼 실제 실행 경로에서 시간 제한을 강제해야 한다.
- `core.batch`는 Future 취소 후 `ThreadPoolExecutor` 종료 대기가 실제 실행 시간을 timeout보다 길게 만들 수 있는지 회귀 테스트로 검증해야 한다.
- `symbolic` 도구는 `core.batch`의 worker thread에서 실행될 때 SIGALRM 기반 timeout이 비활성화되는 경로를 별도로 방어해야 한다.
- HTTP Bearer 토큰 검증은 일반 문자열 비교 대신 constant-time 비교로 교체해 timing side-channel을 줄여야 한다.

## 현 상태 요약

- 공식 pytest, ruff, mypy, 빌드, MCP stdio smoke 검증은 통과한다.
- CI의 Tool count single source guard는 README 첫 문단 형식과 CHANGELOG 미동기화 때문에 실패한다.
- 평가 명령 실행으로 기존 추적 파일은 변경되지 않았고, 본 요구사항 문서만 신규 파일로 추가됐다.
