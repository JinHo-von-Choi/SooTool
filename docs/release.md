# 릴리스 절차

새 버전을 PyPI와 MCP Registry에 게시하는 순서다. 각 단계의 확인이 끝난 뒤 다음 단계로 넘어간다.

```
CI 통과 확인 → 버전 올리기 → CHANGELOG 정리 → 로컬 검증 → 커밋·push → 태그 → GitHub Release
                                                                                    │
                                    PyPI 게시(publish-pypi.yml 자동 실행) ◀──────────┘
                                         │
                                         └─▶ MCP Registry 게시(mcp-publisher)
```

## 1. CI 통과 확인

작업 트리가 깨끗한 최신 master에서 시작한다.

```bash
git checkout master && git pull origin master
make release-preflight
```

`release-preflight`는 GitHub API로 현재 master 커밋의 CI 결과를 확인한다(`GH_TOKEN` 또는 `GITHUB_TOKEN` 필요).

|종료 코드|뜻|
|-|-|
|0|CI 성공|
|1|CI 실패 또는 진행 중|
|2|토큰 없음|
|3|GitHub API 호출 실패|

## 2. 버전 올리기

세 곳의 버전을 같은 값으로 바꾼다. `tests/test_packaging.py`가 일치 여부를 검사한다.

- `pyproject.toml`의 `version`
- `server.json`의 `version`과 `packages[0].version`

그다음 `uv lock`으로 잠금 파일을 갱신한다.

|변경 내용|올릴 자리|
|-|-|
|하위 호환 버그 수정|patch (0.2.0 → 0.2.1)|
|하위 호환 기능 추가|minor (0.2.x → 0.3.0)|
|호환을 깨는 변경|major (0.x → 1.0.0)|

## 3. CHANGELOG 정리

`## [Unreleased]` 아래 내용을 `## [x.y.z] - YYYY-MM-DD` 절로 옮기고, 빈 `## [Unreleased]`를 맨 위에 남긴다. `make draft-changelog`로 커밋 기록에서 초안을 만들 수 있지만 그대로 쓰지 말고 다듬는다.

도구 수가 바뀌었다면 다음 네 곳의 숫자가 `uv run python scripts/count_tools.py`의 결과와 같아야 한다. CI가 문자열로 대조한다.

- README 첫 문단(`N개 계산 도메인 N개 기본 도구 + N개 admin 정책 도구`)
- README 도구 카탈로그 제목
- `pyproject.toml`의 `description`
- CHANGELOG `[Unreleased]`의 `N domains, N base tools, N admin policy-management tools`

## 4. 로컬 검증

```bash
uv run ruff check src/sootool tests scripts
uv run mypy src/sootool scripts
uv run pytest -q --strict-markers
uv run python scripts/policy_stamp.py --check
uv build
```

## 5. 커밋과 태그

```bash
git add pyproject.toml server.json uv.lock CHANGELOG.md
git diff --staged          # 버전 관련 파일만 들어갔는지 확인
git commit -m "chore(release): x.y.z, <한 줄 요약>"
git push origin master     # CI 통과 확인 후 다음으로
git tag -a vx.y.z -m "Release x.y.z"
git push origin vx.y.z
```

## 6. GitHub Release

Release를 발행하면 `publish-pypi.yml`이 실행되어 PyPI에 올린다.

```bash
sed -n '/## \[x.y.z\]/,/## \[/p' CHANGELOG.md | head -n -1 > /tmp/notes.md
gh release create vx.y.z --title "vx.y.z, <제목>" --notes-file /tmp/notes.md
```

워크플로는 빌드 산출물에 GitHub 빌드 출처 증명(attestation)을 만들고 PyPI에 업로드한다. 인증은 PyPI Trusted Publishing(OIDC)이라 API 토큰을 저장하지 않는다.

## 7. PyPI 반영 확인

워크플로가 끝나면(보통 2~5분) 새 버전이 보인다.

```bash
curl -sSL https://pypi.org/pypi/sootool/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

## 8. MCP Registry 게시

PyPI 반영을 확인한 뒤 `server.json`을 게시한다. 소유권은 README의 `mcp-name:` 표식으로 검증된다.

```bash
mcp-publisher login github
mcp-publisher publish --dry-run
mcp-publisher publish
```

## 저장소 설정

master 브랜치 보호 규칙에 CI 매트릭스 세 개를 필수 상태 검사로 지정해 두면, CI가 실패한 커밋은 병합되지 않는다.

- `Test (Python 3.12 / extras=none)`
- `Test (Python 3.12 / extras=symbolic)`
- `Test (Python 3.12 / extras=all)`

PyPI Trusted Publisher 최초 등록과 TestPyPI 수동 업로드는 [.github/workflows/README.md](../.github/workflows/README.md)를 본다.
