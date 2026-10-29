# SooTool 프로젝트 분석 및 평가

- **대상 저장소**: [JinHo-von-Choi/SooTool](https://github.com/JinHo-von-Choi/SooTool) (`/home/nirna/jobs/SooTool`)
- **평가 기준일**: 2026-10-30 · **평가 대상 커밋**: `3a5feef` (master HEAD, 2026-10-14)
- **방법**: 정적 분석 + 테스트 실행 + 런타임 실측 + 심층 코드 감사 3계열(코어 엔진 / 도메인·정책 / 테스트 스위트) + 독립 외부 데이터셋 대조
- **총평**: **코드 품질은 높으나, 현재 master는 릴리스 가능한 상태가 아니다.** 계산 정확도·감사성·보안 설계는 이급이나, 파이프라인이 22일간 붉은 상태로 방치되어 검증·스모크·빌드가 한 번도 실행되지 않았다.
- **발견 결함**: P0 2건 · P1 5건 · P2 3건 · P3 8건. **P0/P1 9건 전부를 직접 재현해 확정**했으며, 심층 감사 에이전트가 보고한 오탐 4건은 배제했다(§7).
- **조치 상태**: P0 2건 · P1 5건 · P2 3건 전부 반영 완료(§"조치 완료 내역"). 로컬 CI 전 단계 통과, 테스트 4,644건 통과. **커밋·푸시 후 원격 CI 반영 필요.**

### 즉시 조치 요약 — 모두 반영 완료

| # | 조치 | 위치 | 규모 | 상태 |
|---|---|---|---|---|
| 1 | `int(...)` 래핑으로 mypy strict 통과 | `src/sootool/modules/geometry/area.py:246` | 1줄 | ✅ 반영 |
| 2 | CHANGELOG 도구 수 275 → 276 | `CHANGELOG.md:10` | 1줄 | ✅ 반영 |
| 3 | master 브랜치 보호 + CI 필수 검사 | GitHub 설정 | 설정 | ✅ 적용 |
| 4 | 음력 추석 테이블 2020~2030 교정 | `src/sootool/modules/datetime_/lunar.py` | 데이터 + 테스트 | ✅ 반영 |

1·2만 고쳐도 CI는 통과하지 않았다 — **두 결함은 서로 독립**이다. 3번 없이는 다음 자동 병합에서 같은 상황이 재발한다.

---

## 조치 완료 내역 (2026-10-30 반영)

이 문서에 기록한 P0/P1/P2 항목 중 아래를 같은 날 반영했다. 미반영 항목은 §6 "권고 조치 순서"에 남겨 두었다.

| # | 항목 | 조치 | 검증 |
|---|---|---|---|
| 1 | mypy 3건 | `geometry/area.py:246` `int(...)` 래핑 | `mypy src/sootool scripts` → 264 files, no issues |
| 2 | CHANGELOG 드리프트 | `275` → `276`, 증가 도구 4종 명시 | CI 가드 재현: README·pyproject·CHANGELOG 4종 grep PASS + 단언 5종 PASS |
| 3 | 음력 표 교정 | KASI 조견표 기준으로 `lengths` 11개 해 재생성 | 월 시작일 136/136 일치, 내부 불변식 11/11 만족, 알려진 설날·추석 11년분 일치 |
| 4 | 회귀 테스트 | 음력 40건(명절 22 + 월 시작일 136 + 불변식 10) | `pytest tests/modules/datetime_/` 40 passed |
| 5 | `_meta` 누락 | `registry.py` 후처리기 게이트를 dict 전체로 확장 | `core.batch`·`core.pipeline` 봉투에 `integrity`+`hints` 부여 확인 |
| 6 | 결정론 유지 | 변동 필드(`elapsed_ms`·`total_time_ms`·`pipeline_id`)를 결과 해시에서 제외 | 배치/파이프라인 3회 실행 → 동일 `result_hash` |
| 7 | 파이프라인 결정론 | `deps_failed` 를 step 선언 순서로 순회 | `PYTHONHASHSEED` 1~12 → 모두 `deps: ['alpha', 'beta']` |
| 8 | 스레드 증폭 | `ORCHESTRATION_DEPTH` 한도(기본 2) 도입 | 16항목 4단계 중첩: 최대 스레드 **5,393 → 65** |
| 9 | 법인세 반올림 | `min_tax` 를 `round_apply` 로 통일 | `rounding=DOWN` → 7,000,003 / `HALF_UP` → 7,000,004 (이전엔 전부 7,000,004) |
| 10 | 감사 id 전파 | `_resolve_audit_id` 구현(sha256 기준 역순 탐색) | activate `audit_id` = 계산 결과 `policy_audit_id` 일치 확인 |
| 11 | 가짜 통과 테스트 | `policy_audit_id` 존재 → 값 단언으로 교체 | `pytest tests/policy_mgmt/test_trace_extension.py` 5 passed |
| 12 | calc 오류 분류 | `Overflow`·`quantize` 실패 → `domain_constraint` | `10**100000000`·`round(1,100000000)` → `internal_error` 에서 `domain_constraint` 로 |
| 13 | 가드 pytest 이관 | `tests/test_tool_count_guard.py` 추가 | 드리프트 주입 시 FAIL / 복구 시 PASS 확인 (음성 검증) |
| 14 | 브랜치 보호 | `master` 에 CI 3종 필수 검사 + 관리자 강제 + 강제 푸시/삭제 금지 | `branches/master/protection` API 확인 |
| 15 | 모듈 README | README 7개 신설 + 11개에 캐스팅 정책 섹션 추가 | ADR-008 의무 준수 (18/18 모듈) |
| 16 | 계약 불변식 테스트 | `test_every_module_readme_documents_its_casting_policy` 추가 | `pytest tests/test_contract_invariants.py` 8 passed |

** 조치 후 최종 검증 (로컬, 커밋 전 워킹 트리 기준)**

| 검증 | 조치 전 | 조치 후 |
|---|---|---|
| `pytest` 전체 | 4,613 passed | **4,644 passed** (신규 31건, 실패 0) |
| `ruff check src tests scripts` | passed | passed |
| `mypy src/sootool scripts` | **3 errors** | **no issues found in 264 files** |
| `policy_stamp.py --check` | 53 files, 0 mismatched | 53 files, 0 mismatched |
| CI 도구 수 가드(grep 4종 + 단언 5종) | **CHANGELOG FAIL** | **전부 PASS** |
| 추석 2027~2030 | 4년 연속 1일 오류 | **KASI 기준 4/4 일치** |
| 배치·파이프라인 `_meta` | 없음 | `integrity` + `hints` 부여 |
| 배치 `result_hash` 결정론 | — | 3회 실행 동일 |
| 파이프라인 의존 오류 순서 | 해시시드마다 변동 | 12개 시드 전부 동일 |
| 법인세 최소세액 반올림 | 5모드 전부 7,000,004 | DOWN 7,000,003 / HALF_UP 7,000,004 |
| calc `10**1e8` | `internal_error` | `domain_constraint` |
| 중첩 배치 최대 스레드 | 5,393 | **58** |

> **원격 반영 상태**: 2026-10-30 03:21(KST) **릴리스 0.3.0 완료.** PR #42(수정)·#43(버전) 를 CI 통과로 병합하고 태그 `v0.3.0` → GitHub Release → PyPI → MCP Registry 게시까지 끝났다. `io.github.JinHo-von-Choi/sootool` 0.3.0 이 레지스트리에 등록됐고, PyPI `sootool==0.3.0` 을 설치해 동작을 확인했다. master 브랜치 보호(CI 3종 필수 검사 + 관리자 강제)가 살아 있어 이제부터 붉은 CI 커밋은 병합되지 않는다.


**아직 미반영(판정 필요)**

- §4.10 산출세액·지방세 절사 단위 — 국세기본법 제18조 적용이 불분명해 사람이 확정해야 하는 항목. 임의로 통일하지 않고 남겨 두었다.
- 배치 타임아웃이 실행 중인 작업을 중단하지 못하는 문제(§4.11, `core/batch.py:92,167`) — 구조적 변경이 필요해 별도 과제로 분리.
- `core.calc` 의 `Tuple` 화이트리스트 정리, 파이프라인 스냅샷 크기 상한 — 영향 범위가 작은 다듬기 작업.

---

## 1. 한눈에 보기

| 항목 | 측정값 | 평가 |
|---|---|---|
| 도구 수 | 286 (기본 276 + 정책 10, admin-gated 4), 계산 도메인 18, 네임스페이스 20 | ✅ 문서·코드 일치 |
| 소스 규모 | 253개 파일 / 42,368 LOC | ✅ 모듈 경계 명확 |
| 테스트 규모 | 237개 파일 / 31,576 LOC / **4,613 tests** | ✅ 테스트/소스 LOC비 0.745 |
| 테스트 실행 | **4,644 passed, 0 failed, 0 skipped** (324초) | ✅ 매우 건전 |
| 테스트 커버리지 | **92.62%** (18,687 stmts / 1,379 미도달) | ✅ 양호 |
| Ruff | All checks passed | ✅ |
| Mypy (strict) | **3 errors** (`geometry/area.py:246`) → 조치 후 **no issues in 264 files** | ✅ 수정 완료 |
| 정책 파일 | 53개 YAML, sha256 불일치 0 | ✅ |
| CI 상태 | **최근 100회 연속 실패** (마지막 성공 2026-10-08) — 로컬 CI 전 단계 통과·브랜치 보호 적용, **커밋·푸시 대기** | ⚠️ 원격 반영 필요 |
| 미출시 기간 | PyPI 0.2.0 이후 **27일** | ❌ |
| 배치 성능 | 500건 / 2.79초, 순서 보존 | ✅ 우수 |
| 결정론 | 동일 입력 → 동일 `result_hash` 재현 확인 | ✅ (단, 예외 1건 §4.5) |

---

## 2. 프로젝트 개요와 강점

SooTool은 LLM의 직접 산수를 차단하기 위한 정밀 계산 MCP 서버다. 설계는 성숙하다.

**핵심 설계 결정 (docs/architecture.md, ADR-001~026)**

- **Decimal 의무화** — 계산 경로에 float 금지. float 유입은 `D(x, allow_float=True)`로 명시.
- **법령 값 외부화** — 세율·공제액을 `policies/<도메인>/<이름>_<연도>.yaml`로 분리, sha256 + 시행일 + 근거 조문 + 고시번호 + 원문 URL 첨부.
- **시점 기반 정책 선택** — `as_of`로 그날 시행 중이던 버전을 골라 재현.
- **감사 가능성** — 모든 응답에 `trace`(공식·입력·단계·출력)와 `_meta.integrity`(입력/결과 해시) 부착, `sootool receipt verify`로 재실행 대조 가능.
- **결정론** — `deterministic=True` 기본, 난수 시드 고정, 배치 결과는 입력 id 순 재정렬.

**검증된 강점 (직접 실측)**

| 항목 | 결과 |
|---|---|
| 정책 무결성 | 53개 YAML 전수 sha256 재계산 → 0 불일치. 로더가 로드 시점에 해시를 검증하고 변조 파일은 `PolicyIntegrityError`로 거부 |
| 연도 처리 | 미지원 연도 호출 → `UnsupportedPolicyError`. 정책 도구 41종 전부 `year` 필수 |
| float 누출 | 세무·급여·금융·회계·부동산·tax_us 계열에서 float 유입 0건. float은 stats/probability/pm/medical 등 ADR-008이 허용한 영역에만 존재 |
| 계산 샌드박스 | `eval`/`exec`/`compile` 미사용. `__import__`, `().__class__`, `eval`, `open`, 컴프리헨션, walrus, f-string 전부 차단 확인 |
| 배치 성능 | 500건 배치 2.79초(프로세스 기동 포함), 전건 성공, 입력 순서 완전 보존 |
| 영수증 | `receipt verify` 재실행 대조 `valid: true`, 불일치 0 |
| 결정론 | 동일 입력 2회 실행 → `input_hash`·`result_hash` 완전 일치 |
| 패키징 | wheel에 정책 YAML 53개 포함, `py.typed` 동봉, `pip install` 경로 정상 |
| 보안 기본값 | 비루프백 바인딩 시 토큰 없으면 기동 거부, `--remote-admin`은 관리자 토큰 필수, `hmac.compare_digest` 상수시간 비교, Unix 소켓 0600, 정책 쓰기는 admin 모드 + `policy-write` 스코프 이중 게이트, `yaml.SafeLoader`만 사용 |
| 문서 정합성 | README/pyproject의 도구 수 문자열은 실측과 일치. `scripts/count_tools.py` 단언 5종 전부 통과 |

> **ADR-019의 "숫자 단일 소스" 장치는 실제로 작동한다.** 아래 §4.1의 CHANGELOG 드리프트를 정확히 잡아내었다. 문제는 장치가 아니라 그것을 읽는 humans/agent 프로세스다.

---

## 3. 구조적 강점: "정답처럼 보이는 오답"을 없애는 설계

프로젝트의 핵심 주장(LLM이 숫자를 틀린다 → 도구가 정확히 계산한다)은 벤치마크로 뒷받침된다. `bench/results/2026-04-24-sota.md` 기준 20문항:

| 풀이 주체 | exact | approx | wrong |
|---|---|---|---|
| **SooTool** | **20** | 0 | 0 |
| gemini-3-pro-preview | 12 | 4 | 4 |
| claude-opus-4-7 | 9 | 3 | 8 |
| gpt-5.4 | 5 | 3 | 12 |

README 표는 이 SOTA 실행본을 정확히 인용하고 있다(별개로 `2026-04-24-final.md`에 구모델(gpt-4o / claude-sonnet-4-5 / gemini-2.5-pro) 실행본이 남아 있으나, 동일 날짜 파일명이라 혼동 여지가 있다 — 사소).

---

## 4. 발견 사항 (우선순위 순)

### 4.1 [P0] CI가 22일간 붉은 상태 — 검증·스모크·빌드가 단 한 번도 실행되지 않음

**증거**

- 최근 CI 실행 **100건 전부 `failure`** (2026-04-23 이래 전량 조회).
- 마지막 성공: **2026-10-08**. 그 이후 100회 연속 실패.
- 실패 지점은 전부 **Mypy 스텝**. GitHub Actions Job 로그:
  ```
  ✓ Set up job / ✓ Checkout / ✓ Install uv / ✓ Sync dependencies / ✓ Ruff
  X Mypy        ← 여기서 종료
  - Pytest      ← 실행 안 됨
  - Policy hash check      ← 실행 안 됨
  - Tool count single source guard (ADR-019)  ← 실행 안 됨
  - MCP smoke (stdio / HTTP / SSE / Unix)    ← 실행 안 됨
  - Build distributions / Validate __version__  ← 실행 안 됨
  ```
- 즉 **2주간 정책 해시 검증, 도구 수 대조, 4종 MCP 전송 스모크 테스트, 배포 빌드가 한 번도 실행되지 않았다.** 성공한 마지막 빌드가 무엇을 담고 있는지 알 수 없다.

**원인 1 — mypy 타입 오류 (독립 결함)**

`src/sootool/modules/geometry/area.py:246`
```python
span = (
    max(value.adjusted() for value in coordinates)
    - min(value.as_tuple().exponent for value in coordinates) + 1
    if coordinates else 1
)
```
`Decimal.as_tuple().exponent`의 타입은 `int | Literal['n','N','F']` (NaN/무한대는 문자열). mypy strict가 이 연산을 거부한다.

- **런타임 오류는 아니다.** 유한한 Decimal의 exponent는 항상 `int`이며, 코드 앞부분에서 `is_finite()`를 검사한다. `geometry.area_polygon` 실측 정상 동작(3-4-3 삼각형 → `6`).
- **수정안 검증 완료**: `min(int(value.as_tuple().exponent) for ...)` 적용 시 오류 3건이 모두 소거됨(격리 프로브로 확인).
- 회귀 도입 커밋: `bca3ce2` (#31, 2026-10-13). 이 커밋부터 CI가 붉어졌다.

**원인 2 — CHANGELOG 도구 수 드리프트 (독립 결함)**

`CHANGELOG.md:10`은 `18 domains, 275 base tools`라고 선언하지만 실측은 `276`. CI 가드(`.github/workflows/ci.yml:67`)가 이 문자열을 grep하므로 **이것도 단독으로 CI를 막는다.** mypy만 고쳐도 CI는 여전히 붉다.

- 실측: `total=286 base=276 policy=10 domains=18`
- README 2개 패턴, pyproject 1개 패턴: **PASS**. CHANGELOG 1개 패턴: **FAIL**.
- 수정안 검증 완료: `[Unreleased]` 절의 `275` → `276` 교체 시 가드 통과.

> 두 결함은 서로 독립이며, **둘 다 고쳐야 CI가 통과한다.** 어느 쪽도 사람의 개입을 기다리지 않고 자동 감지되도록 설계되어 있었으나, CI가 이미 붉은 상태에서 시작된 탓에 어느 쪽도 눈에 띄지 않았다.

**방치의 구조적 원인**

`master`에 **브랜치 보호가 없다** (`gh api .../branches/master/protection` → `Branch not protected`). 자동화 봇이 만든 PR 40개가 CI 실패와 무관하게 master에 병합됐다(전부 `feat: autonomous SooTool evolution`). 마지막 커밋(2026-10-14) 이후 16일간 활동이 없다.

릴리스 쪽은 fail-closed로 설계되어 있어 형편이 낫다.
- `scripts/release_preflight.py`는 현재 HEAD의 CI 상태를 조회해 실패 시 exit 1 → **정상 동작 확인** (실행 시 CI 실패를 정확히 감지).
- `.github/workflows/publish-pypi.yml:48`도 `uv run mypy src/sootool`을 게이트로 사용 → 릴리스도 mypy 오류로 차단됨.
- **PyPI 0.2.0(2026-10-03) 이후 27일간 릴리스 없음** — 게이트가 작동한 결과이며, 이는 의도된 안전장치다.

**권고**
1. `area.py:246`에 `int(...)` 래핑 (1줄)
2. `CHANGELOG.md:10`의 `275` → `276` (1줄)
3. **`master` 브랜치 보호 + CI 필수 검사** (`require_status_checks`) — 자동 병합 봇이 CI를 무시할 수 없게 하는 게 핵심
4. CI 1단계 실패 시 알림 (PR/봇에 "CI red" 통지) — 2주간 무인 상태가 된 직접적 원인이 이것이다

---

### 4.2 [P0] 추석 날짜가 4년 연속(2027~2030) 1일씩 틀림 — 사용자 영향이 직접적인 정확도 결함

프로젝트의 존재 이유("정답처럼 보이는 오답을 없애라")에 정면으로 충돌하는 결함이다.

**독립 검증 결과** — KASI 기반 한국 음력 구현(`korean-lunar-calendar`)과 전수 대조:

| 음력년 | SooTool 설날 | KASI 설날 | SooTool **추석** | KASI **추석** | 판정 |
|---|---|---|---|---|---|
| 2025 | 2025-01-29 | 2025-01-29 | 2025-10-06 | 2025-10-06 | ✅ |
| 2026 | 2026-02-17 | 2026-02-17 | 2026-09-25 | 2026-09-25 | ✅ |
| 2027 | 2027-02-07 | 2027-02-07 | **2027-09-16** | **2027-09-15** | ❌ **+1일** |
| 2028 | 2028-01-27 | 2028-01-27 | **2028-10-02** | **2028-10-03** | ❌ **−1일** |
| 2029 | 2029-02-13 | 2029-02-13 | **2029-09-21** | **2029-09-22** | ❌ **−1일** |
| 2030 | 2030-02-03 | 2030-02-03 | **2030-09-11** | **2030-09-12** | ❌ **−1일** |

설날 앵커는 6년 전부 정확하고, 명절 전체(설날·대보름·부처님오신날·단오·칠석) 21건 대조 중 **불일치는 추석 4건뿐**이다. 결함은 `_LUNAR_YEARS`의 2027~2030 월 길이 테이블에 국한된다.

**코드 내부 자기모순 (외부 데이터 없이도 증명 가능)** — `src/sootool/modules/datetime_/lunar.py:88, 94`

| 음력년 | 선언된 월 길이 합 | 다음 설날까지 실제 일수 | 차이 |
|---|---|---|---|
| 2026 | 355 | 355 | 0 ✅ |
| **2027** | **355** | **354** | **+1 ❌** |
| **2028** | **384** | **383** | **+1 ❌** |
| 2029 | 355 | 355 | 0 ✅ |

음력 한 해는 월 길이 합과 그해 설날→다음해 설날 간격이 **반드시 같아야 한다.** 2027·2028은 표 안의 두 값이 서로 1일 어긋난다 — 외부 권위 자료 없이도 오류가 확정된다.

**테스트가 왜 잡지 못했나**

`tests/modules/datetime_/test_lunar.py`는 추석을 **2024·2025 두 해만** 고정 assertion 한다. 두 해는 우연히 정답이다. 2026~2030은 assertion이 없어 잘못된 값이 그대로 통과한다. → §5의 "권장 추가 테스트" 1순위.

**영향 범위**: `datetime.lunar_holiday` (추석), `datetime.lunar_to_solar`, `datetime.solar_to_lunar`. 음력 ↔ 양력 상호변환이므로 2027~2030 음력 날짜를 직접 조회하는 모든 호출이 영향을 받는다. 추석은 한국 최대 명절이라 휴무·일정·급여 정산에 실제 피해가 발생한다.

**권고**: `korean-lunar-calendar` 또는 KASI 달력자료로 2020~2030 전체 월 길이 테이블을 재생성하고, 외부 기준선 대조 테스트를 추가.

---

### 4.3 [P1] `core.batch` / `core.pipeline` 응답에 `_meta`가 전혀 없음 — ADR-021·ADR-015 위반

`src/sootool/core/registry.py:205`
```python
if isinstance(result, dict) and "trace" in result:
    for proc in self._post_processors:
```
포스트프로세서(integrity·hints 주입)가 `"trace"` 키 존재를 조건으로 하는데, `BatchResult`/`PipelineResult`에는 `trace` 키가 없다.

**실측**
```
core.batch 응답 최상위 키: ['count_error','count_ok','count_timeout','parallelism','results','status','total_time_ms']
has _meta: False
```
`core.pipeline`도 동일. (항목별 내부 결과에는 `_meta`가 주입되지만 **외부 봉투는 유실된다.**)

**위반**: ADR-021("모든 도구 응답에 `_meta.integrity` 블록을 자동 주입"), ADR-015("모든 도구 응답이 `_meta.hints` 배열을 포함"). 배치·파이프라인이 제품의 대표 기능(README "한 번에 최대 500건")인데, 가장 많이 쓰는 경로에서만 영수증이 사라진다. 배치 결과를 파일로 보관해 감사 later에 재검증하려는 사용자는 봉투 단위로는 그럴 수 없다.

**권고**: `trace` 키 존재 조건 대신 "도구 호출 결과"를 판별하는 공통 마커(예: 결과 객체에 `_is_tool_result` 속성 부여 또는 `BatchResult`/`PipelineResult`에 `trace` 스텁 추가)로 조건을 완화.

---

### 4.4 [P1] 중첩 `core.batch`가 스레드 풀을 곱셈으로 증폭 — 단일 요청으로 수천 스레드

`src/sootool/core/batch.py:70` — `pool = ThreadPoolExecutor(max_workers=workers)`. `core.batch`는 `read_only=True`이므로 자기 자신을 호출할 수 있다. 호출 깊이 제한이 없고, 유일한 브레이크는 인자 깊이(`ARG_DEPTH=16`)와 노드 수 제한이다.

**심층 감사 실측**: 항목 16개 × 중첩 깊이 4 → **최대 스레드 5,393개, RSS 260MB, 13.3초 소요, 전건 타임아웃(`status: all_failed`)** — 유용한 출력 0.

**위반**: ADR-007(도메인 모듈은 병렬 호출에 안전해야 함)의 취지를 넘어, 서버 프로세스 자원을 한 요청이 고갈시킬 수 있다. MCP 서버는 보통 여러 클라이언트가 공유하는 장기 실행 프로세스다.

**권고**: 호출 깊이 제한(예: 2~3)을 `core.batch`/`core.pipeline`에 강제하고, 깊이를 넘으면 명시적 오류 반환. 배치 실행기는 실행 컨텍스트에 "현재 중첩 깊이"를 실어 재진입을 차단.

---

### 4.5 [P1] 파이프라인 의존 실패 메시지가 프로세스마다 달라짐 — ADR-011 결정론 위반

`src/sootool/core/pipeline.py:167` — `graph: dict[str, set[str]]`. `pipeline.py:258-261`이 이 **set**을 순회해 `deps_failed` 목록을 만든다.

**직접 재현** (동일 입력, `PYTHONHASHSEED`만 변경):
```
seed=1   -> deps: ['beta', 'alpha']
seed=2   -> deps: ['alpha', 'beta']
seed=3   -> deps: ['beta', 'alpha']
seed=5   -> deps: ['alpha', 'beta']
seed=11  -> deps: ['alpha', 'beta']
```
문자열 해시 시드가 프로세스마다 달라지므로(set 순회 순서도 달라짐) **동일 입력 → 다른 응답 본문 → 다른 `result_hash`.** ADR-011(동일 입력 → 동일 출력)의 위반이다. 이 프로젝트의 영수증 재실행 검증이 성립하는 전제 자체가 깨진다.

**원인**: `graph`를 `set`으로 선언. TopologicalSorter에 넘기는 단계에서는 dict 삽입 순서를 쓰므로 DAG 실행 순서는 이미 결정론적이나, **오류 메시지 조립만 set 순서를 그대로 노출**한다.

**권고**: `deps_failed`를 `sorted(...)`로 정렬하거나, `graph`를 삽입 순서를 보존하는 구조(list of dict)로 변경.

---

### 4.6 [P1] `tax.kr_corporate` 최소세액이 호출자의 반올림 지시를 무시 — ADR-002 위반

`src/sootool/modules/tax/kr_corporate.py:175`
```python
min_tax = min_tax_raw.quantize(Decimal("1")) if decimals == 0 else min_tax_raw
```
`rounding=` 인자가 없다 → 앰비언트 컨텍스트의 `ROUND_HALF_EVEN`이 적용된다. 같은 함수의 `base_tax`는 호출자의 `policy_enum`을 따른다.

**실측** (`taxable_income=100000050`, `is_small=true` → 원시 최소세액 7,000,003.50):
```
rounding=DOWN       -> minimum_tax = 7000004   ← DOWN이면 7000003이어야 함
rounding=HALF_UP    -> minimum_tax = 7000004
rounding=HALF_EVEN  -> minimum_tax = 7000004
rounding=CEIL       -> minimum_tax = 7000004
rounding=UP         -> minimum_tax = 7000004
```
**5가지 반올림 모드가 전부 동일한 값을 낸다** — ADR-002(반올림은 호출자가 선택, 기본값 금지) 위반. 법령이 정한 절사 규칙과 사용자가 지정한 반올림 중 어느 쪽이 맞는지 판단할 여지조차 없이, 지시가 무시되고 있다.

**권고**: `quantize(Decimal("1"), rounding=policy_enum)`로 일관화.

---

### 4.7 [P1] 정책 덮어쓰기의 `audit_id`가 계산 trace에 전달되지 않음 — ADR-016 위반 + 테스트가 이를 구조적으로 감지 불가

`src/sootool/policy_mgmt/trace_ext.py:86-91`
```python
def _resolve_audit_id(source: str, policy_version: dict[str, Any]) -> str | None:
    """For override policies, look up the most recent activate audit entry."""
    if source != "override":
        return None
    # We don't cache the audit lookup, it's a one-time read per response
    return None  # Filled in by tools that have the draft_id available
```
`source == "override"` 분기에도 **`return None`으로 떨어진다.** 함수는 어느 경로에서도 값을 반환하지 않는다. 주석의 "Filled in by tools that have the draft_id available"은 구현되지 않은 상태다.

**엔드투엔드 재현 (직접 실행)**
```
propose  -> draft_id = drf-f19a1e74235d4489bbf43a3ffd1a1c12
activate -> audit_id = aud-9205b6180407480796201b9bc44e32c1

calc tool (tax.kr_income) after override activation:
  trace.policy_source    = override          ← 덮어쓰기 적용은 정상 인식
  trace.policy_audit_id = None               ← 감사 id는 전달되지 않음
  activate audit_id     = aud-9205b618...
  MATCH?                = False
```

**왜 테스트가 못 잡는가** — `tests/policy_mgmt/test_trace_extension.py:21`
```python
assert "policy_audit_id" in result
```
**키의 존재만** 확인한다. 값이 항상 `None`이어도 통과한다(실측: 위 재현에서 `in result` → `True`). 즉 이 테스트는 계약 위반을 통과시키도록 되어 있다.

**왜 중요한가** — ADR-016은 "audit_id는 계산 도구 trace에 `policy_audit_id`로 전파된다", "덮어쓰기 여부를 호출자가 항상 식별 가능하게 한다"를 규정한다. 사용자가 정책 덮어쓰기(`policy_source=override`)로 세법을 바꿨을 때, **어느 감사 항목이 그 변경의 근거인지 계산 결과에서 추적할 수 없다.** 정책 관리 도구의 존재 이유(감사 가능성)가 계산 경로에서 끊긴다. 다만 `policy_source`와 `policy_sha256`는 전달되므로 "덮어쓰기 여부 식별"은 되고, "어느 감사 항목인지"만 비어 있다.

**권고**: `_resolve_audit_id`를 실제로 구현해 최근 activate 감사 항목을 조회하도록 만들고, 테스트를 **값 기반**으로 바꾼다:
```python
assert result["policy_audit_id"] == activate_result["audit_id"] == audit_log[-1]["audit_id"]
```

---

### 4.8 [P2] `core.calc`에서 `Overflow`·`InvalidOperation`이 오류 분류 밖으로 누출

`src/sootool/core/calc/_evaluator.py:152-155`, `:334-335` — `_apply_binop_decimal`이 `DivisionByZero`/`InvalidOperation`만 처리한다. `decimal.Overflow`는 그 형제(sibling)라 잡히지 않는다. `round()`의 `quantize()`도 무방어.

**실측**
```
10**100000000      -> code=internal_error  type=Overflow
round(1,100000000) -> code=internal_error  type=InvalidOperation
```
**위반**: ADR-025(도구 오류는 typed code), ADR-017(도메인 위반 → `DomainConstraintError`). 사용자에게 "내부 오류"로 보이는 것은 도메인 제약 위반이며, "값이 너무 크다"는 의미의 정직한 오류 코드여야 한다.

참고로 샌드박스 자체는 견고하다: `__import__('os')`, `().__class__` → `disallowed_operation`, `1/0` → `domain_constraint`, `sqrt(-1)` → `domain_constraint`. 탈출 시도 차단은 확인된 범위에서 모두 차단되었다.

---

### 4.9 [P2] ADR-008이 요구한 모듈 README의 "내부 자료형 및 캐스팅 정책" 섹션 부재

`docs/architecture.md:51`은 **각 모듈 README에 "내부 자료형 및 캐스팅 정책" 섹션을 의무화**한다.

- README가 있는 11개 모듈 전부에서 해당 섹션 없음.
- README 자체가 **없는 모듈 7개**: `math`, `payroll`, `pm`, `probability`, `science`, `symbolic`, `tax_us`.
- 계약 위반을 감지하는 테스트도 없다(`tests/test_contract_invariants.py`는 도구명·버전·오류코드·영수증 필드·SDK 공개명만 검증).

ADR-008의 자료형 이원화(Decimal / float64 / mpmath)는 이 프로젝트의 정확성 설계의 근간인데, 그 정책이 도메인별로 어떻게 적용되는지가 문서로 고정돼 있지 않다.

**권고**: 모듈 README에 템플릿 섹션을 추가하고, 계약 불변식 테스트로 "모든 모듈 README에 해당 섹션 존재"를 검증.

---

### 4.10 [P2] 산출세액 반올림 규칙이 모듈 간 불일치 (사람의 판단 필요)

같은 `kr_income` 세율구간을 쓰는데 반올림이 다르다.

- `src/sootool/modules/tax/kr_comprehensive_income_tax.py:128` — `RoundingPolicy.DOWN` (절사)
- `src/sootool/modules/payroll/kr_year_end_tax_settlement.py:144` — `RoundingPolicy.HALF_UP`

`tax/README.md:33`은 "규칙 없는 끝수는 원 단위 절사"라고 명시하므로, 연말정산 쪽이 자신의 모듈 README와 모순된다.

**참고**: 국세기본법 제18조(원미만 올림)의 적용이 불분명해 **어느 쪽이 법적으로 옳은지는 사람 판단이 필요하다.** 다만 지금은 같은 개념이 두 값을 내므로, 적어도 하나는 틀렸다.

덧붙여 `tax/kr_local_income_tax.py:36,43`은 지방소득세를 1원 단위로 버림하고 있어, `tax/README.md:33`·`docs/user_guide.md:48`·`payroll/kr_salary.py:14`의 "지방세 10원 미만 절사" 규칙과 내부 모순이다. 역시 판정 필요.

---

### 4.11 [P3] 경미한 사항

| 항목 | 위치 | 내용 |
|---|---|---|
| 파이프라인 스냅샷 무제한 | `core/pipeline.py:27-28` | TTL(10분) eviction만 있고 크기 상한이 없어, 300회 호출 시 스냅샷 300개가 각자의 전체 결과와 `_meta.integrity`를 보관 |
| 앰비언트 Decimal 컨텍스트 | `core/decimal_ops.py:7` | `getcontext().prec = 50`이 현재 스레드 컨텍스트를 변조. 코어 경로는 `submit_with_context`로 안전하게 복사하지만 `modules/symbolic/_bridge.py:147`은裸 풀을 씀 |
| `get_rng` 공유 생성기 | `core/determinism.py:26-45` | 캐시된 `Generator`를 반환해 동시 사용 시 스트림이 섞임. 현재 `src/` 호출자 없음(죽은 코드) |
| `core.calc` Tuple 화이트리스트 | `core/calc/_rules.py:16` | ADR-017은 Call 인자 위치에서 허용하지만 평가기 분기가 없어 `sum((1,2))`가 `disallowed_operation`으로 거부됨(실용성 문제) |
| `solar_terms` 고정 날짜 | `datetime_/lunar.py:348-374` | 소한 1/6, 경칩 3/6 등 일부 연도 1일 오차. ±1일 허용으로 문서화되어 있음 |
| 배치 타임아웃의 의미 | `core/batch.py:92,167` | `fut.cancel()`은 실행 중 future를 취소하지 못함. `item_timeout_s=0.5`로 6초짜리 작업이 0.5초에 반환돼도 워커 스레드는 6.65초까지 유지됨 — `batch_timeout_s`가 수행 작업량을 제한하지 않음 |
| README 영수증 예시 | `README.md:199-203` | `--receipt receipt.json`이 무엇인지 명시 안 함. CLI 헬프는 "`_meta.integrity` JSON 파일"이라 함. 그대로 쓰면 `tool_missing` 등 4개 오류로 실패 |
| 벤치 결과 파일 2벌 | `bench/results/` | 동일 날짜(2026-04-24) 파일 2개(`final`=구모델, `sota`=현모델). README는 `sota`를 정확히 인용하나 어느 쪽인지 파일명만으로는 불명확 |
| `dist/` 잔여 산출물 | 저장소 루트 | 0.1.1~0.1.3 wheel/sdist가 커밋된 채 방치. `.gitignore`은 있으나 작업 디렉터리 정리를 위함 |

---

## 5. 테스트 스위트 평가

**측정 결과**

| 지표 | 값 |
|---|---|
| 전체 실행 | 4,613 passed / 0 failed / 0 skipped / 0 xfailed / 222 warnings (310.73초) |
| 총 커버리지 | **92.62%** (18,687 stmts / 1,379 미도달) |
| `core/` | 94.31% (118 미도달) |
| `policy_mgmt/` | 93.66% (111 미도달) |
| `middleware/` | 100.00% (0 미도달) |
| `transports/` | 73.45% (47 미도달) |
| `sdk/` | 14.93% — 단, `sdk/_typed.py`(465 stmts)는 **생성물이고 런타임 미임포트**. 이를 제외하면 91.21% |

**강점**

- **skip/xfail 0건.** 알려진 결함을 격리해 둔 곳이 없다. 전체가 통과하거나 실패한다.
- **ADR-007 요구 충족**: N≥50 병렬 동일성 테스트가 54곳에 있으며 **18개 도메인 전부** 커버.
- **ADR-020 요구 충족**: `tests/core/test_batch.py:121, 152`에 지정된 회귀 테스트 2건이 실제로 명명된 속성을 검증한다(순서 테스트는 수집 순서가 새면 실패, 벽시계 테스트는 실측 0.30초 vs 상한 0.6초).
- 237개 테스트 파일 AST 스캔 결과, 테스트 로컬 재구현과의 자기참조 비교(tautology)는 발견되지 않음.

**약점**

| ID | 심각도 | 내용 |
|---|---|---|
| T1 | HIGH | **§4.7과 동일** — `policy_audit_id` 존재만 assert하는 테스트(`tests/policy_mgmt/test_trace_extension.py:21`)가 계약 위반을 통과시킨다 |
| T2 | HIGH-MED | **ADR-007 assertion이 공허하다.** `tests/modules/engineering/test_thermal.py:296-312`는 `Decimal(res["lmtd"]) > Decimal("0")`만, `test_fluid.py:334-352`는 키 존재 + `> 0`만 검증 → **어떤 양수 값이어도 통과.** 나머지 engineering 동시성 테스트 4건도 입력을 1..100으로 변주해 "상태 격리"만 검증하고 ADR이 요구한 "동일 결과"는 검증하지 않는다 |
| T3 | MED | **네트워크 admin 게이트가 4개 쓰기 도구 중 1개만 커버.** `tests/transports/test_http_e2e.py:89-99`는 `policy_rollback`만 호출. `policy_propose/activate/import`은 전송 계층에서 한 번도 호출되지 않음. 게이트는 "admin 모드 **AND** policy-write 스코프" 이중 조건(`_tool_common.py:36-43`)인데, `mode=ON + read 스코프 ⇒ 거부` 케이스를 검증하는 테스트가 없음. 또한 4개 도구는 전 도구 오류 스위프(`tests/core/test_boundary.py:244-247`)에서 제외돼 있음 |
| T4 | MED | **ADR-017이 요구한 오류 메시지 미검증.** `tests/core/test_calc.py:94-97`은 55개 케이스에서 예외 타입만 확인. 노드 종류 + 위치를 담은 메시지(`disallowed Subscript: subscript access (line 1, col 0)`)를 검증하는 테스트가 없고, `Starred`/`Yield` 명시 케이스도 없음 |
| T5 | MED | **"정답"이 구현에서 파생된 값이다.** `bench/cases.yaml:17`의 기대값은 `REGISTRY.invoke` 실행 결과이며, `tests/bench/test_cases_yaml.py:97-108`은 구현을 그 값과 비교 → 드리프트 스냅샷이지 독립적 진실이 아님. 독립 계층(`tests/scenarios/kr_official_examples.yaml`, 출처 URL 포함 48개 시나리오)은 263개 도구 중 14개, 3개 네임스페이스만 커버 |
| T6 | MED-LOW | **틀린 숫자에도 통과하는 assertion.** `tests/modules/crypto/test_arithmetic.py:61-63`은 `int(result["result"]) > 0` (정답은 2), `tests/modules/finance/test_risk.py:14-22`는 `var > 0` (정답 0.0775). `test_risk.py:57,65`, `test_option.py:203`, `test_metrics.py:94`도 동일 패턴 |
| T7 | LOW | ADR-020 벽시계 테스트가 `wall < 0.6s` 하드코딩(`test_batch.py:149`) — 순차 실패 지점 0.75초에 근접. ADR-023의 `SOOTOOL_TIMEOUT_TOLERANCE` 우회도 무시. 순서 테스트는 "완료 순서가 실제로 뒤집혔는가"를 확인하지 않음 |
| T8 | LOW | **서브프로세스 커버리지 사각지대.** `__main__.py` 34%, `transports/stdio.py` **0%**, `transports/http.py` 58%는 측정 아티팩트. `tests/transports/test_multi.py:84-209`가 `python -m sootool` 서브프로세스로 테스트하는데 pytest-cov가 서브프로세스를 계측하지 않음(`pyproject.toml`에 설정 없음). **동작은 커버되나 수치가 신뢰 불가** |
| T9 | LOW | ADR-019 가드가 CI 전용. `tests/test_docs_catalog.py:28-35`는 README 표만 검증하고 README 첫 문단·CHANGELOG·pyproject 숫자는 검증하지 않음 → §4.1의 CHANGELOG 드리프트를 pytest가 잡지 못한 이유 |
| T10 | LOW | 원자적 tmp→rename 미검증. `tests/policy_mgmt/test_drafts.py:103-119`는 0600 권한만 확인, `.tmp` 잔여물 부재와 실패 시 기존 파일 보존은 미검증 |

**커버리지 하위 10개 파일 (미도달 라인 수)**

`sdk/_typed.py` 465 (0%, 생성물) · `__main__.py` 86 (34%) · `core/calc/_evaluator.py` 51 (79%) · `modules/finance/metrics.py` 42 (84%) · `modules/science/optics.py` 35 (81%) · `modules/symbolic/_bridge.py` 27 (79%) · `policy_mgmt/validators.py` 23 (90%) · `policy_mgmt/schemas.py` 22 (96%) · `modules/engineering/electrical.py` 17 (89%) · `modules/engineering/fluid.py` 17 (94%)

**추가 권장 테스트 (우선순위)**

1. `test_policy_audit_id_matches_audit_log` — activate → 계산 도구 호출 → `trace["policy_audit_id"] == activate["audit_id"] == audit_log[-1]["audit_id"]` (T1 노출)
2. HTTP admin 게이트를 **4개 쓰기 도구 전체**에 파라미터화 (read 토큰 ⇒ `admin_required`, admin 토큰 ⇒ 성공) + 프로세스 내 `SOOTOOL_ADMIN_MODE=1` + `scopes={read}` ⇒ 거부 케이스 (T3)
3. engineering의 공허한 assertion 2건을 기대값 고정 assertion으로 교체, 미커버 219개 도구에 동일 입력 N=100 테스트 추가 (T2)
4. `DisallowedOperationError` 메시지에 노드 종류와 `line`/`col`이 들어가는지 노드 타입별로 assert + `Starred`/`Yield` 명시 케이스 (T4)
5. `gcd == 2`, `var == 0.0775` 등 정확값 고정 assertion (T6)
6. `_atomic_write_yaml`의 `.tmp` 잔여물 부재 + 실패 시 기존 파일 보존 assertion (T10)
7. `bench`의 `test_sootool_ground_truth` → `test_matches_frozen_snapshot`으로 개명 (T5)

---

## 6. 권고 조치 순서

### 즉시 (릴리스 차단 해제 — 총 2줄 변경)

1. `src/sootool/modules/geometry/area.py:246` → `min(int(value.as_tuple().exponent) for value in coordinates)`
2. `CHANGELOG.md:10` → `275 base tools` → `276 base tools`
3. CI 통과 확인 후 `master` 브랜치 보호 활성화(CI 필수 검사) + 봇/사람이 CI red를 무시하고 병합할 수 없게 함
4. 4.2(추석) 수정과 함께 릴리스 노트에 명시

### 이번 스프린트

5. 음력 테이블 2020~2030 재생성(KASI 권위 데이터) + **2026~2030 추석 assertion 추가**
6. `core.batch`/`core.pipeline` `_meta` 복구 (§4.3)
7. 파이프라인 `deps_failed` 정렬로 결정론 복구 (§4.5)
8. `core.batch` 호출 깊이 제한으로 스레드 증폭 차단 (§4.4)
9. `kr_corporate` 최소세액 반올림 일관화 (§4.6)
10. `_resolve_audit_id` 구현 + 값 기반 테스트로 교체 (§4.7, §5 T1)

### 다음 스프린트

11. `core.calc` `Overflow`/`InvalidOperation` → 도메인 제약 오류 코드화 (§4.8)
12. 모듈 README 7개 작성 + 캐스팅 정책 섹션 추가 + 계약 불변식 테스트 (§4.9)
13. 산출세액·지방세 절사 단위 판정(법률 검토 후 단일 규칙 확정) (§4.10)
14. `core.calc` `Tuple` 화이트리스트 정리 및 파이프라인 스냅샷 크기 상한 (§4.11)
15. §5의 권장 테스트 7건 반영 (공허 assertion 2건 교체, admin 게이트 4종 파라미터화, 정확값 고정)

### 프로세스

16. **자동화 봇이 병합하기 전에 반드시 CI green을 요구하는 규칙**을 PR 템플릿/봇 설정에 명문화. 이번 사고의 실질적 원인은 코드가 아니라 "붉은 CI를 2주간 아무도 보지 않는" 프로세스였다.
17. 가드 장치가 CI 1단계에서 실패하면 즉시 알림이 가도록 한다(그렇지 않으면 §4.1의 2개 결함 중 2번째는 영원히 발견되지 않았을 것이다).
18. ADR-019 도구 수 대조를 pytest로도 옮겨 CI 전용 의존(T9)을 제거한다.

---

## 7. 검증에서 배제된 항목 (오탐 정리)

심층 감사에서 보고되었으나 직접 재현·검증 결과 **오탐으로 판명**한 항목이다. 그대로 옮기면 잘못된 수정 작업을 유발할 수 있어 기록한다.

| 보고 항목 | 검증 결과 |
|---|---|
| `payroll.kr_salary`가 `as_of`를 무시하고 연말 버전을 항상 로드 | **오탐.** `as_of` 미지정 → 2026-11-01 버전(304,000), `as_of=2026-03-01` → 2026-01-01 버전(302,575), `as_of=2026-08-01` → 2026-07-01 버전(304,000). 정상 동작 |
| `tax.kr_withholding_simple`이 2026-01-01~02-28 구버전을 도달 불가로 만듦 | **오탐.** `as_of=2026-02-01` 지정 시 `effective_date: 2026-01-01, effective_to: 2026-02-28`의 superseded 버전이 정상 선택됨 |
| `payroll.kr_health_income_premium`가 잘못된 정책 버전을 사용 | **오탐.** `as_of`에 따라 2026-01-01 / 2026-10-01 버전이 정상 전환됨. (버전 내부의 `threshold_basis` 분기는 별도 사양 문제) |
| README 벤치 표의 모델명이 실제 벤치와 불일치 | **오탐.** README은 `2026-04-24-sota.md`(gpt-5.4 / claude-opus-4-7 / gemini-3-pro-preview)를 정확히 인용함. `final.md`는 구모델 실행본 |
| `core.batch`의 항목별 결과에 `_meta`가 없음 | **부분 오탐.** 항목별 `result` 내부에는 `_meta`가 주입됨. **외부 봉투**만 유실(§4.3) |

---

## 8. 부록: 검증 방법과 재현 절차

**실행한 검증**

| 검증 | 명령 | 결과 |
|---|---|---|
| 전체 테스트 | `uv run pytest -q --no-header` | 4,613 passed / 0 failed / 0 skipped / 0 xfailed, 310.73s |
| 커버리지 | `uv run pytest -q --cov=sootool --cov-report=term-missing` | 92.62% (18,687 stmts / 1,379 미도달) |
| 린트 | `uv run ruff check src tests` | All checks passed |
| 타입 | `uv run mypy src/sootool scripts` | 3 errors in 1 file |
| 정책 해시 | `uv run python scripts/policy_stamp.py --check` | 53 files checked, 0 mismatched |
| 도구 수 | `uv run python scripts/count_tools.py --json --assert-*` | 286 / 276 / 10 / 4 / 18 — 단언 통과 |
| CI 가드 재현 | `.github/workflows/ci.yml:52-74` 단계 로컬 재현 | README·pyproject PASS, **CHANGELOG FAIL** |
| CI 이력 | `gh run list --limit 200` | 101건 중 100건 실패, 마지막 성공 2026-10-08 |
| 브랜치 보호 | `gh api .../branches/master/protection` | `Branch not protected` (404) |
| 릴리스 게이트 | `uv run python scripts/release_preflight.py` | 정상 동작 (CI 실패 감지 후 exit 1) |
| 배치 성능 | `core.batch` 500항목 | 2.79s, 전건 ok, 입력 순서 보존 |
| 결정론 | 동일 입력 2회 실행 | `input_hash`·`result_hash` 일치 |
| 영수증 | `receipt verify` 재실행 대조 | `valid: true`, 불일치 0 |
| 음력 대조 | `korean-lunar-calendar`(KASI 기반) 전수 대조 | 21건 중 4건 불일치 (추석 2027~2030) |
| 음력 자기모순 | 표의 월 길이 합 vs 설날 간격 | 2027 (355 vs 354), 2028 (384 vs 383) — 1일 어긋남 |
| 파이프라인 결정론 | `PYTHONHASHSEED` 1~12 | 오류 메시지 순서 변동 재현 |
| 정책 감사 id 전파 | propose→activate→계산 도구 호출 | `policy_audit_id=None` (감사 id 미전파) |
| 샌드박스 | `core.calc` 탈출 시도 일괄 | 전부 차단 |
| 패키징 | `uv build --wheel` | 정책 YAML 53개 + `py.typed` 동봉 |

**산출 계산**: 이 프로젝트의 자체 CLI(`sootool call core.div` 등)로 수행했다(직접 산술 금지 원칙 준수).

**미검증 영역 (남은 불확실성)**

- 산출세액·지방세 절사 단위(§4.10)는 법률 판단이 필요한 영역으로, 기술 감사로는 "모순 존재"까지만 확인했다.
- `bench/`의 LLM 비교는 본 평가 범위 밖(재현에 유료 API 키 필요).
- 성적/바이너리 배포물(`dist/`)의 재현성은 미검증.
- 서브프로세스로 기동하는 경로(`transports/stdio.py` 등)의 커버리지 수치는 측정 아티팩트다(§5 T8).
- 심층 코드 감사 3계열(코어 엔진 / 도메인·정책 / 테스트 스위트)은 독립 에이전트가 수행했고, 본 문서의 모든 **P0·P1 발견은 부모가 직접 재현·검증**했다(§7 오탐 정리 참조). 에이전트가 보고한 P2 이하 항목 중에는 직접 확인하지 않은 것이 포함될 수 있다.

---

*작성: 2026-10-30 · 본 문서의 모든 수치는 위 절의 명령으로 재현 가능하다.*
