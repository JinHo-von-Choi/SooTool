# GitHub Actions Workflows

## `ci.yml` — 지속 통합

트리거: `master`/`main` 푸시 및 PR.

실행 단계: uv sync → ruff → mypy → pytest → MCP stdio 스모크 → uv build → `__version__` 검증.

## `publish-pypi.yml` — PyPI 배포

트리거:
- GitHub Release 발행 시 자동 (`release: types: [published]`) → PyPI 공개 업로드
- 수동 (`workflow_dispatch`) → PyPI 또는 TestPyPI 선택 업로드

인증 방식: PyPI Trusted Publishing (OIDC). API 토큰 저장 불필요.

### 1회성 초기 설정 (PyPI 계정에서 직접 수행 필요)

1. https://pypi.org/manage/account/publishing/ 접속 후 "Add a new pending publisher" 클릭
2. 다음 값 입력:
   - PyPI Project Name: `sootool`
   - Owner: `JinHo-von-Choi`
   - Repository name: `SooTool`
   - Workflow name: `publish-pypi.yml`
   - Environment name: `pypi`
3. TestPyPI 동일 절차: https://test.pypi.org/manage/account/publishing/ 에서 environment name `testpypi` 로 등록

### 2회차 이후 릴리즈 절차

1. 로컬에서 `pyproject.toml` 버전 bump 및 CHANGELOG 갱신 후 커밋
2. `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`
3. GitHub 웹에서 Release 생성 (태그 지정, 릴리즈 노트 작성) 또는 `gh release create vX.Y.Z --notes-from-tag`
4. Release `published` 이벤트가 `publish-pypi.yml` 을 자동 트리거하여 PyPI 업로드
5. 업로드 완료 후 https://pypi.org/project/sootool/ 에서 확인

### 수동 TestPyPI 테스트

GitHub 웹 Actions 탭 → "Publish to PyPI" → "Run workflow" → `target: testpypi` 선택. 업로드 후 `pip install -i https://test.pypi.org/simple/ sootool` 로 검증.

### Environment 보호 (선택)

`pypi` environment 에 리뷰어 승인을 설정하면 릴리즈 자동 트리거 후에도 수동 approval 이 필요해진다. Settings → Environments → pypi → Required reviewers.
