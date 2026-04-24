# SooTool 릴리스 절차

작성자: 최진호
작성일: 2026-04-24

이 문서는 SooTool 패키지를 PyPI에 배포하는 표준 절차를 기술한다.
모든 단계를 순서대로 따르고, 각 단계의 검증을 완료한 후에만 다음으로 진행한다.

---

## 1. master 브랜치 최신 상태 확인

```
git checkout master
git pull origin master
git status  # working tree가 clean해야 한다
```

로컬 변경사항이 없어야 한다. 미완성 작업이 있으면 별도 브랜치로 이동 후 진행한다.

---

## 2. CI green 대기

릴리스 전 현재 HEAD의 CI가 반드시 green이어야 한다.

방법 A — 스크립트 사용 (권장):

```
make release-preflight
```

exit 0이면 CI 성공 확인 완료. exit 1이면 CI 실패이므로 원인 수정 후 재시도.
exit 2이면 GitHub 토큰이 없으므로 GH_TOKEN 환경변수를 설정한 후 재실행한다.

방법 B — GitHub Actions UI 직접 확인:

https://github.com/JinHo-von-Choi/SooTool/actions 에서
현재 master 최신 커밋의 CI 런이 초록(success) 상태인지 확인한다.

---

## 3. pyproject.toml 버전 범프

`pyproject.toml`의 `[project]` 섹션에서 `version` 값을 증가시킨다.

규칙:
- 하위 호환 버그 수정 → patch 증가 (예: 0.1.3 → 0.1.4)
- 하위 호환 기능 추가 → minor 증가 (예: 0.1.x → 0.2.0)
- 하위 비호환 변경 → major 증가 (예: 0.x.y → 1.0.0)

```
# pyproject.toml 예시
[project]
version = "0.1.4"
```

---

## 4. CHANGELOG.md 업데이트

`CHANGELOG.md`의 `[Unreleased]` 섹션을 새 버전 항목으로 변환한다.

순서:
1. `## [Unreleased]` 헤더 바로 아래에 새 `## [Unreleased]` 헤더와 빈 섹션을 삽입한다.
2. 기존 내용을 `## [x.y.z] - YYYY-MM-DD` 헤더로 이동한다 (오늘 날짜 사용).

예시:

```
## [Unreleased]

## [0.1.4] - 2026-04-24

### Added
- ...

### Fixed
- ...
```

`scripts/draft_changelog.py`가 있다면 초안 생성 후 사람이 검토·편집한다.
자동 생성 결과를 검토 없이 그대로 릴리스하지 않는다.

---

## 5. 로컬 검증

변경 후 전체 품질 게이트를 로컬에서 통과해야 한다.

```
uv run ruff check src/sootool tests scripts
uv run mypy src/sootool scripts
uv run pytest -q --strict-markers
uv build
```

4개 명령 모두 오류 없이 완료되어야 한다.
`uv build`로 생성된 `dist/` 산출물도 이후 단계에서 사용된다.

---

## 6. 커밋

```
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): x.y.z — <한 줄 요약>"
```

커밋 메시지에 Co-Authored-By 라인을 포함하지 않는다.
범프 외 다른 파일이 포함되지 않도록 `git diff --staged`로 확인한다.

---

## 7. 태그 및 push

```
git tag -a vx.y.z -m "Release x.y.z"
git push origin master
git push origin vx.y.z
```

두 push 모두 성공해야 한다. push 후 GitHub Actions에서 CI가 다시 실행되어
통과하는지 확인한다.

---

## 8. GitHub Release 생성

태그 push 후 GitHub Release를 생성하면 `publish-pypi.yml`의
`release: types: [published]` 이벤트가 트리거되어 PyPI 업로드가 자동 진행된다.

gh CLI 사용:

```
gh release create vx.y.z \
  --title "vx.y.z — <제목>" \
  --notes "$(sed -n '/## \[x.y.z\]/,/## \[/p' CHANGELOG.md | head -n -1)"
```

또는 GitHub UI에서 https://github.com/JinHo-von-Choi/SooTool/releases/new 에서
해당 태그를 선택하여 수동 생성한다.

GitHub REST API를 직접 사용하는 경우:

```
curl -s -X POST \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/JinHo-von-Choi/SooTool/releases \
  -d '{"tag_name":"vx.y.z","name":"vx.y.z — <제목>","body":"<내용>","draft":false}'
```

---

## 9. PyPI 반영 확인

Release 생성 후 publish-pypi.yml 워크플로우가 완료되면 PyPI에 새 버전이 등록된다.
일반적으로 2~5분 소요된다.

```
curl -sSL https://pypi.org/pypi/sootool/json | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['version'])"
```

출력이 새 버전 번호(예: 0.1.4)이면 릴리스 완료.

pip 설치로도 확인할 수 있다:

```
pip install --upgrade sootool
python -c "import sootool; print(sootool.__version__)"
```

---

## 다음 단계: Branch Protection 활성화

master 브랜치에 branch protection rule을 활성화하면 CI red 상태의 push 및
PR 머지를 차단할 수 있다.

GitHub 저장소 Settings > Branches > Add rule에서 다음을 설정한다:

- Branch name pattern: `master`
- Require status checks to pass before merging: 체크
- 필수 체크 (ci.yml matrix 3개 모두 추가):
  - `Test (Python 3.12 / extras=none)`
  - `Test (Python 3.12 / extras=symbolic)`
  - `Test (Python 3.12 / extras=all)`
- Require branches to be up to date before merging: 체크

branch protection이 적용되면 `make release-preflight`와 이중 게이트가 구성되어
CI red 릴리스를 구조적으로 방지할 수 있다.

긴급 hotfix 시에는 repository owner 권한으로 admin bypass를 사용한다.
