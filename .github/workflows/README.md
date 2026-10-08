# GitHub Actions 워크플로

## ci.yml

`master`, `main`으로의 push와 PR에서 실행한다. Python 3.12에서 선택 설치 조합 세 가지(`extras=none`, `symbolic`, `all`)로 각각 돈다.

```
uv sync → ruff → mypy → pytest → 정책 해시 검사 → 도구 수 대조 → MCP 연결 점검(stdio, HTTP, SSE, Unix) → uv build → __version__ 확인
```

도구 수 대조 단계는 `scripts/count_tools.py`가 레지스트리에서 센 숫자가 README, `pyproject.toml`, CHANGELOG의 숫자와 같은지 확인한다. 도구를 추가하거나 지웠다면 네 곳을 함께 고친다([docs/release.md](../../docs/release.md) 3절).

## publish-pypi.yml

|트리거|동작|
|-|-|
|GitHub Release 발행(`release: published`)|PyPI에 업로드|
|수동 실행(`workflow_dispatch`)|`target`으로 PyPI 또는 TestPyPI 선택|

빌드 산출물에 출처 증명(attestation)을 만든 뒤 Trusted Publishing(OIDC)으로 업로드한다. 저장소에 PyPI API 토큰을 두지 않는다.

### Trusted Publisher 최초 등록

PyPI 계정에서 한 번만 한다.

1. https://pypi.org/manage/account/publishing/ 에서 "Add a new pending publisher"
2. 입력값
   - PyPI Project Name: `sootool`
   - Owner: `JinHo-von-Choi`
   - Repository name: `SooTool`
   - Workflow name: `publish-pypi.yml`
   - Environment name: `pypi`
3. TestPyPI는 https://test.pypi.org/manage/account/publishing/ 에서 같은 값으로, Environment name만 `testpypi`로 등록한다.

### TestPyPI로 시험 업로드

Actions 탭 → "Publish to PyPI" → "Run workflow" → `target: testpypi`. 업로드 뒤 `pip install -i https://test.pypi.org/simple/ sootool`로 설치해 본다.

### 배포 승인 단계 추가(선택)

Settings → Environments → `pypi` → Required reviewers를 지정하면 Release를 발행해도 승인 전까지 업로드하지 않는다.
