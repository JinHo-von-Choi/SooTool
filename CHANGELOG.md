# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

REGISTRY 수치: 18 domains, 271 base tools, 10 admin policy-management tools (0.1.4 대비 base 17개 증가: sootool.verify_receipt, core.solve_for, core.compare, core.explain, payroll.kr_gross_from_net, tax_us.fica, tax.kr_eitc, tax.kr_securities_transaction, tax.kr_pension_income, tax.kr_vehicle_tax, tax.kr_registration_license_tax, realestate.kr_subscription_score, payroll.kr_overtime_pay, payroll.kr_weekly_holiday_pay, payroll.kr_minimum_wage_check, payroll.kr_national_pension_benefit, payroll.kr_health_income_premium).

### Added

- 명령줄 서브커맨드(ADR-027): `sootool call|tools|batch|pipeline|receipt verify|policy|skill-guide|version`. 서브커맨드가 없으면 기존처럼 서버로 기동한다. MCP와 같은 레지스트리 경로, 같은 인자 검증과 오류 계약을 쓰며 종료 코드는 0, 1(도구 오류), 2(입력 오류), 3(관리자 모드 필요), 70(내부 오류)이다. 출력 형식은 `pretty`, `json`, `raw`, `trace`다.
- 분석 도구 3종과 역산 도구: `core.solve_for`(읽기 전용 도구의 결과 필드가 목표값이 되는 숫자 입력을 Decimal 이분법으로 역산), `core.compare`(기준안 대비 시나리오 값과 차이), `core.explain`(수식, 입력, 계산 단계, 결과, 적용 정책과 근거 조문을 한국어·영어 평문으로 서술하며 수치는 바꾸지 않음), `payroll.kr_gross_from_net`(세후 월급에서 세전 월급을 구한다. 실수령액이 목표 이상이 되는 가장 작은 원 단위 월급과 달성 실수령액, 잔차를 반환). 모두 결정적이며 영수증 재실행 검증이 가능하고 정책 도구의 `as_of`를 따른다. `core.solver`는 순수 Decimal 이분법이다.
- 요청 단위 컨텍스트(`sootool.core.request_context`)와 `RequestContextMiddleware`: 요청마다 Accept-Language 로케일, 무상태 표식, 인증 범위를 설정한다. Accept-Language 가 `sootool.skill_guide`의 로케일에 실제로 반영된다.
- 인증 범위: `SOOTOOL_AUTH_TOKEN`은 `read`, `SOOTOOL_ADMIN_TOKEN`(또는 `--admin-token`)은 `read`와 `policy-write` 범위를 부여한다. 정책 쓰기는 관리자 모드와 `policy-write` 범위를 모두 요구한다. `--admin` 플래그를 추가했다.
- 오류 계약(`sootool.boundary`): 오류 클래스별 고유 코드와 구조화된 오류 결과. SDK 단계의 거부(알 수 없는 도구, 인자 누락, 타입 오류)도 같은 형식이다.
- 입력 숫자 허용: 문자열 숫자 파라미터가 JSON 숫자도 받는다(입력 스키마는 string 유지).
- 네트워크 전송 스모크 스크립트(`scripts/mcp_smoke_{http,sse,unix}.py`)를 v2 클라이언트로 다시 작성하고 CI 에 추가했다.
- 인자 크기 검사: 모든 호출 경로(stdio, 네트워크, 프로세스 내, batch·pipeline 중첩)에서 문자열 길이(10만자), 목록·객체 원소 수(10만), 중첩 깊이(16), 전체 노드 수(100만)를 검사한다. 도구별 한도를 행렬 크기(200), 다항식 차수(256), FFT 표본 수(65,536), crypto 정수 자릿수(2,048), 영업일 구간(10만 일)으로 확대했다. 모든 한도는 `SOOTOOL_LIMIT_<이름>`으로 조정한다. 한도 경계 입력의 최악 실행 시간은 시험으로 고정한다(호출당 15초 이내, 실측 대부분 4초 이내). 신호 기반 호출 시간 중단은 SDK v2가 동기 도구를 워커 스레드에서 실행해 쓸 수 없어 입력 한도로 실행 시간을 묶는다.
- 도구 검색 별칭(`sootool.core.tool_aliases`): 양도세, 종부세, 집 팔 때 세금 같은 줄임말과 일상 표현, 영어 동의어로 `sootool.search`를 찾는다. 38개 현실 질의 중 별칭 없이 11개가 상위 3위 밖이던 것을 모두 상위 3위 안으로 올렸다.
- `tools/list` 결과에 `ttlMs`(1시간)와 `cacheScope`(public)를 싣고 도구를 이름 순으로 고정한다(MCP 2026-07-28).
- 시점·조문 인지 정책 엔진(ADR-026): 정책 헤더 v2(`effective_to`, `status`, `version`, `citations`, `reviewed_by`)와 같은 연도의 다중 버전(`<name>_<year>@<시행일>.yaml`). 정책 기반 도구 27개와 `policy_get`, `policy_export`가 공통 인자 `as_of`(YYYY-MM-DD)와 `include_proposed`를 받는다. 결과에 `policy_status`, `policy_effective_to`, `policy_citations`와 `_meta.integrity.policy_*`가 실리고 개정안 결과에는 `proposed_policy_in_use` 힌트가 붙는다. 영수증 검증은 같은 버전으로 재현된다.
- 정책 검증: 헤더 v2 필드 형식, 인용 구조, 같은 연도 확정 버전의 시행 기간 겹침을 검사한다. 활성화는 시행일이 다르면 새 버전 파일을 만들고 `policy_rollback`은 `effective_date`로 버전을 고른다.
- `scripts/policy_stamp.py`: 정책 자체 해시 갱신과 검사(CI에 `--check` 추가).
- 계산 영수증 재실행 검증: `_meta.integrity`에 `tool`과 `result_hash`(중첩 `_meta`를 제외한 응답 본문의 정규화 sha256)를 추가했다. 새 도구 `sootool.verify_receipt`가 `tool`, `arguments`, `receipt`로 같은 계산을 다시 실행해 도구 이름, 입력 해시, 결과 해시, 도구 버전, 정책 해시를 대조한다. `core.batch`, `core.pipeline`, `core.pipeline_resume`은 결과에 실행별 값이 있어 검증 대상에서 제외한다.
- 영수증 선택 서명: 환경변수 `SOOTOOL_RECEIPT_KEY_FILE`에 base64 ed25519 개인 키 파일 경로를 지정하면 스탬프에 `key_id`와 `signature`가 추가된다. 키는 파일 경로로만 참조한다. 키 파일을 읽을 수 없으면 계산 결과는 그대로 반환하고 `signature_error` 코드를 남긴다. `verify_receipt`는 `public_key_b64`가 있으면 서명을 검증하고 `require_signature`로 서명 필수를 강제할 수 있다.
- `sootool.core.signing`: 정책 번들과 영수증이 공유하는 ed25519 기반 함수.
- 계산 엔진 등급 표기: 응답 `_meta.engine`과 `sootool.describe`의 `engine` 필드가 `decimal`, `mpmath`, `float64`, `composite`, `none` 중 하나를 알려준다. 도구가 정의된 모듈의 임포트를 정적으로 분석해 가장 거친 엔진을 등급으로 삼는 보수적 분류이며, 다른 모듈에 위임하는 도구는 명시 지정한다. `float64` 결과는 근사값이다.

- `sootool.core.limits`: 도구 호출 단위 입력 한도의 단일 출처. 환경변수 `SOOTOOL_LIMIT_<이름>`으로 조정. 초과 입력은 `InputLimitError`(`DomainConstraintError` 하위)로 계산 전에 거부한다.
- 한도 적용 도구: `probability.factorial`·`nCr`·`nPr`, `crypto.is_prime`, `finance.loan_schedule`·`irr`, `math.integrate_simpson`·`integrate_gauss_legendre`, `datetime.add_business_days`, `core.calc`(precision), `stats.bootstrap_ci`, `pm.monte_carlo_schedule`.

- 모든 도구에 MCP 어노테이션(`readOnlyHint`, `idempotentHint`, `openWorldHint`)을 선언했다. 정책 쓰기 도구 4종은 `readOnlyHint=false`이며 덮어쓰기 성격의 3종에 `destructiveHint`를 선언한다. `REGISTRY.tool`에 `read_only`, `destructive`, `idempotent` 인자를 추가했다.
- 정책 번들 서명 시험(서명·검증 왕복, 변조 탐지, 잘못된 키 입력, import 연동) 추가.
- 공식 MCP Registry 등록 준비: `server.json`, README의 `mcp-name` 표식, 버전 일치 검사 시험, 릴리스 절차 문서.
- `sootool.core.lazy`: 무거운 의존 모듈의 지연 로딩 프록시.
- 노출 프로파일 `--profile {full,lean}`(환경변수 `SOOTOOL_PROFILE`). `lean`은 `sootool.search`, `sootool.describe`, `sootool.call`, `sootool.skill_guide` 4종만 노출한다(`tools/list` 약 2.4KB, `full`은 약 173KB). 기본값은 `full`이며 동작이 바뀌지 않는다.
- `sootool.core.catalog`: 도구 검색(결정적 점수 순위), 설명, 인자 검증.
- 신규 도구 12개: `tax_us.fica`(FICA, 자영업자 SECA 포함), `tax.kr_eitc`(근로장려금), `tax.kr_securities_transaction`(증권거래세와 농특세), `tax.kr_pension_income`(연금소득 원천징수와 분리과세), `tax.kr_vehicle_tax`, `tax.kr_registration_license_tax`, `realestate.kr_subscription_score`(청약 가점), `payroll.kr_overtime_pay`, `payroll.kr_weekly_holiday_pay`, `payroll.kr_minimum_wage_check`, `payroll.kr_national_pension_benefit`, `payroll.kr_health_income_premium`. 법정 상수는 정책 YAML(조문 인용 포함)에 있고 시행일별 버전을 지원한다.
- 도구 결과 스키마: 모든 도구가 도구별 TypedDict 로 결과 구조를 선언하고 `outputSchema` 로 공개한다(`sootool.core.result_types`). 시험 중 모든 도구 호출의 결과를 선언한 타입으로 검증한다. 공개 스키마는 공통 외피(`_meta`, `trace`, 정책 출처)를 줄여 `tools/list` 응답을 약 0.4MB 로 유지한다.
- 응답 `_meta.input_coerced`: JSON 부동소수로 받은 문자열 숫자 인자가 배정밀도 표기로 바뀐 경우 인자 이름과 변환값을 알린다.
- 정책 시행일별 버전 파일: 4대보험(2026-07-01, 2026-11-01), 간이세액표(2026-03-01 자녀 세액공제), 최저임금(2027), 양도소득세와 종합부동산세 등 2027 개정안(proposed).
- 라이브러리 인터페이스 `sootool.sdk`(ADR-028): MCP 서버 없이 같은 도구를 파이썬 함수로 호출한다. 결과, 영수증, 정책 `as_of`, 오류 계약이 MCP 와 같고 도구별 결과 타입 선언(`sdk/_typed.py`)으로 타입 검사가 된다. 실행 기반을 `sootool.runtime`(mcp 비의존)으로 분리해 도메인 하나를 불러와 첫 호출까지 약 0.35~0.5초가 든다. pint 단위 레지스트리를 첫 사용 때 만들어 단위 변환을 쓰지 않는 호출과 서버 기동 비용을 줄였다(서버 전체 기동 약 2.2~2.6초에서 약 1.7~2.0초). 코드 실행 환경 레시피는 `docs/sdk.md`.
- 도구 메타데이터 조회 지점 `ToolSpec`(`sootool.core.toolspec`): 엔진, 정확도 등급(exact, high_precision, approximate, depends_on_children, not_numeric), 별칭, 결과 타입, 파라미터를 한 구조로 모은다. `sootool.describe` 가 `exactness` 를 함께 반환한다. 도구 전체 목록 `docs/tool_catalog.md` 는 레지스트리에서 생성하며 README 표의 도구 수와 함께 시험으로 검사한다.
- 폐기 예고 표기: 도구 정의의 `deprecated`(대체 도구, 제거 예정 버전)가 도구 목록 설명 앞부분, `describe` 결과, 응답 `_meta.deprecated` 에 나타난다. 호환 약속과 폐기 절차는 `docs/stability.md`.
- 도구 설명 전체를 목적, 입력 단위, 반올림 규칙, 대표 오용 순으로 보강하고 검색 별칭을 확대했다.

### Breaking

- MCP SDK v2(`mcp>=2.3,<3`)와 MCP 2026-07-28 사양으로 이행했다. SDK v1 은 지원하지 않는다. 자세한 내용은 ADR-025.
- WebSocket 전송을 제거했다(`--transport websocket`, `--enable-websocket`, `--ws-port`, `SOOTOOL_ENABLE_WEBSOCKET`). `--transport websocket` 은 이전 방법을 안내하는 오류로 종료한다.
- Unix 소켓 전송은 줄 단위 JSON-RPC 대신 UDS 위의 Streamable HTTP(`/mcp`)로 서비스한다. 기존 줄 단위 클라이언트는 호환되지 않는다. 소켓은 요청한 권한(기본 0600)으로 바인드 시점부터 생성하며 기본 경로는 `$XDG_RUNTIME_DIR/sootool/sootool.sock`이다.
- HTTP+SSE 전송은 폐기 경고를 남기며 다음 마이너 릴리스에서 제거한다.
- 네트워크 전송(HTTP, SSE, Unix)은 무상태다. 호출 이력이 필요한 힌트 규칙은 stdio 와 프로세스 내 호출에서만 동작하며 네트워크 응답에는 `_meta.session_stats`가 없다. `SOOTOOL_SESSION_ID` 환경변수를 제거했다.
- 오류 응답 형식이 바뀌었다. 모든 도구 오류는 `isError` 결과이며 `structuredContent.error`에 `code`, `message`, `retryable`(과 `field`, `details`)을 담는다. 선언되지 않은 인자는 더 이상 무시되지 않고 `invalid_arguments`로 거부된다.
- `D()`와 `core.div`가 비숫자 입력과 0 나눗셈에 `InvalidNumberError`, `DivisionByZeroError`를 낸다(`decimal.InvalidOperation`, `ZeroDivisionError`도 함께 상속).
- 정책 쓰기 도구는 로컬 전송(stdio, unix)에만 노출한다. 네트워크 전송에 노출하려면 `--admin --remote-admin --admin-token`이 필요하다.

- `sootool.policy_export` 의 `private_key_b64` 인자를 없앴다. 서명 키는 환경변수 `SOOTOOL_POLICY_KEY_FILE` 이 가리키는 파일(권한 0600)에서 읽는다. 서명 키가 도구 호출 기록에 남지 않게 하기 위해서다. `include_signature` 가 참인데 키 파일이 없으면 오류를 낸다(이전에는 서명 없이 내보냈다).

### Changed

- 선형회귀(`stats.regression_linear`)를 statsmodels 대신 numpy/scipy 로 계산한다(교차 시험으로 같은 결과 확인). 기본 의존성에서 statsmodels(pandas 포함)와 사용하지 않던 workalendar, numpy-financial 을 뺐다. statsmodels 는 교차 시험용 dev 의존성이다.
- scipy.stats, scipy.interpolate, statsmodels를 해당 도구의 첫 호출 시점에 불러온다. 전체 모듈 로드 기동 시간이 약 4.2~4.7초에서 약 2.2~2.6초로, 기동 직후 메모리가 약 209MB에서 약 92MB로 줄었다(측정 환경 기준).
- 정책 초안 기본 경로를 `/tmp` 대신 `$XDG_RUNTIME_DIR` 또는 `$XDG_STATE_HOME/sootool/drafts`로 옮겼다. 초안, 정책 덮어쓰기, 감사 로그 디렉터리는 소유자 전용(0700)으로 준비하며 심볼릭 링크, 다른 사용자 소유, 비디렉터리는 `UnsafeDirectoryError`로 거부한다.
- `core.batch`와 `core.pipeline`이 읽기 전용으로 선언된 도구만 실행한다(`ToolRegistry.invoke_read_only`). 두 도구의 `readOnlyHint` 선언과 `sootool.call`의 읽기 전용 제한이 중첩 호출에도 일관되게 적용된다.
- 설명이 짧던 도구 23종의 설명을 입력 형식, 단위, 반환 필드까지 보강했다.
- `cryptography`를 직접 의존성으로 선언했다. 서명 검증은 잘못된 키·서명 입력을 `SignatureVerificationError`로, 잘못된 개인 키를 `InvalidInputError`로 반환한다.
- MCP 노출 경로가 `REGISTRY.invoke`를 거치도록 정리했다. 모든 MCP 응답에 `_meta.integrity`와 `_meta.hints`가 일관되게 포함된다.
- `mcp[cli]` 의존 범위를 `>=1.27,<2`로 지정했다.
- `_meta.integrity.input_hash`가 기본값 인자를 채운 정규화 입력으로 계산된다. 직접 호출과 MCP 호출, 기본값 생략과 명시 호출이 같은 해시를 갖는다.
- 확률 조합 도구의 대형 정수 결과가 4300자리 변환 한계와 무관하게 문자열로 직렬화된다.

### Fixed

- 법정 값과 계산 규칙을 조문 기준으로 정정했다: 근로소득 간이세액표(별표 2 전체를 데이터로 내장, 근사 공식 폐기), 양도소득세(1세대1주택 비과세, 고가주택 안분, 표 2 장기보유특별공제, 중과), 증여세와 상속세 공제, 법인세율, 간이과세 매입세액 공제, 취득세·종합부동산세·재산세, 대출 규제 비율, 국민연금·건강보험·장기요양 요율과 기준소득월액, 퇴직소득세와 연말정산 공제 한도, 미국 연방·CA·NY 세율과 장기 양도소득 누적 과세.
- `float64` 엔진 도구가 지수 표기 결과의 지수 끝 0 을 지워 값이 10배로 바뀌던 오류(예: `7.33e-10` 이 `7.33e-1`).
- `symbolic.solve` 와 `symbolic.diff` 가 소수 리터럴과 치환 값을 배정밀도로 처리해 해의 자릿수를 잃던 문제(정확한 유리수로 처리).
- 영업일 가감(`datetime.add_business_days`)이 과거 방향 계산에서 이전 연도 공휴일을 빠뜨리던 오류.
- `payroll.kr_gross_from_net` 이 간이세액표 행 경계에서 실수령액이 줄어드는 구간을 이분법으로 잘못 풀 수 있던 문제.
- 에이전트 가이드의 플레이북과 예시 다수가 실행되지 않던 문제(인자 이름, 단계 결과 참조 경로, 지원하지 않는 연도). 모든 플레이북과 예시를 실행하는 시험을 추가했다.
- 형식이 잘못된 정책 YAML 이 예외로 끝나던 문제를 검증 오류 보고로 바꿨다. 정책 저장 경로에 쓰이는 입력(영역, 이름, 시행일, 초안 식별자)의 형식을 검증하고 검증에 실패한 초안은 활성화하지 않는다.
- 신고 유형별 구간표를 가진 정책(tax_us)을 `policy_validate` 와 `policy_propose` 로 검증하면 오류로 멈추던 문제.

## [0.1.4] - 2026-04-24

Release quality uplift. `docs/plans/2026-04-24-release-quality-improvements.md` 계획의 P0~P2 전 항목 반영. 기능 도구 추가 없음. REGISTRY 수치 0.1.3과 동일(18 domains, 254 base tools, 10 admin policy-management tools, 5 transport modes).

### Added
- `scripts/release_preflight.py`, stdlib `urllib.request`로 GitHub Actions API를 호출하여 현재 master commit의 CI `conclusion="success"`를 사전 검증하는 릴리스 게이트. `gh` CLI 의존 없음(snap gh의 cgroup 제약 회피). 토큰 해석 순서 `GH_TOKEN` → `GITHUB_TOKEN` → `~/.config/gh/hosts.yml` → `~/snap/gh/current/.config/gh/hosts.yml`. 403/5xx 지수 백오프 2회.
- `scripts/draft_changelog.py`, git log + REGISTRY 스냅샷 기반 `[Unreleased]` 초안 자동 생성. Conventional Commits 매핑(feat·fix·chore·docs·refactor·perf·test·build·ci·style·security → Added·Fixed·Changed·Security·Unclassified). `--since`/`--until`/`--write` 지원.
- `tests/core/test_timeout_contracts.py`, 7 케이스 시간 축 계약 테스트. `BatchExecutor.batch_timeout_s`·`item_timeout_s`, `PipelineExecutor.step_timeout_s`·`pipeline_timeout_s`, `symbolic _EVAL_TIMEOUT_S`(메인 스레드 SIGALRM 경로 + 비메인 스레드 ThreadPoolExecutor watchdog 경로)의 실제 wall-clock 구속을 실측. `SOOTOOL_TIMEOUT_TOLERANCE` 환경변수로 CI flake 방지.
- `docs/release.md`, 9단계 릴리스 절차 문서. master CI green 사전 검증부터 PyPI 반영 확인까지. branch protection required status check 3종(`Test (Python 3.12 / extras=none|symbolic|all)`) 안내.
- `SECURITY.md`, 공급망 신뢰 검증 3경로 문서화: `gh attestation verify`, `sigstore verify identity`, GitHub Attestations 브라우저 페이지.
- `docs/architecture.md` ADR-023 "Release Gate, Timeout Contracts, Optional Extras Matrix", R1(릴리스 게이트), R2(시간 축 계약 7 테스트), R3(optional extras 매트릭스) 3개 계약을 규범화. ADR-018 번호는 CLI 서브커맨드 계획 예약 존중.
- `docs/architecture.md` ADR-019 Appendix, `base_tools = total_tools − policy_tools` 공식을 규범으로 고착. CI 5종 단언(total·base·domains·policy·admin) 명시.

### Changed
- `Makefile`: `release-preflight`, `draft-changelog` 두 타깃 추가.
- `scripts/count_tools.py`: `--assert-base`, `--assert-namespaces` 옵션 추가. human print 라벨 `= 전체 - policy`로 이미 정렬된 base 공식을 CLI 단언으로도 강제.
- `.github/workflows/ci.yml`: matrix 확장 `extras: [none, symbolic, all]`. `Sync dependencies` step이 extras 값에 따라 `uv sync --frozen` 또는 `uv sync --frozen --extra <n>`으로 분기. Tool count guard step에 `--assert-base "$BASE"`·`--assert-admin 4` 추가. job name이 `Test (Python 3.12 / extras=<n>)` 세 개로 분리되며 branch protection required status checks도 3종으로 변경해야 한다.
- `.github/workflows/publish-pypi.yml`: build 잡 permissions에 `id-token: write`·`attestations: write`·`contents: read` 명시. `actions/attest-build-provenance@v1` step(`subject-path: 'dist/*'`) 추가. `pypa/gh-action-pypi-publish@release/v1`의 `attestations: true` 활성화. release 이벤트 시 sigstore bundle을 GitHub Release asset으로 업로드(`gh release upload ... dist/*.sigstore.bundle --clobber`).
- `pyproject.toml`: `[project.optional-dependencies]`에 `all = ["sootool[symbolic]"]` 메타 extra 추가. 향후 extra는 `all`에 누적.
- `tests/modules/symbolic/test_diff.py`·`test_solve.py`: `pytest.importorskip("sympy")` 상단 삽입. `extras=none` 환경에서 자동 skip되어 `import sootool` 의 sympy-free 계약을 방어.

### Fixed
- 0.1.1·0.1.2 릴리스가 CI red 상태에서 진행되고 0.1.2는 publish 빌드 잡 실패로 PyPI 업로드가 스킵됐던 원인을 구조적으로 차단: `release_preflight.py` + branch protection + extras matrix 3종 CI 검증으로 "우회 허용" 경로를 제거.
- `BatchExecutor`/`PipelineExecutor`/`symbolic _bridge`의 timeout이 필드만 존재하고 강제력이 없었던 선언-실장 갭을 실제 wall-clock 계약 테스트로 회귀 방어.

### Notes
- branch protection rule에 required status checks로 `Test (Python 3.12 / extras=none)`, `Test (Python 3.12 / extras=symbolic)`, `Test (Python 3.12 / extras=all)` 세 개를 GitHub UI에서 추가하는 것이 ADR-023 R1 완성의 마지막 수동 조치. 코드 변경으로는 불가.

[0.1.4]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.4

## [0.1.3] - 2026-04-24

Infrastructure hotfix for the 0.1.2 release: the GitHub Actions CI and
Publish-to-PyPI workflows were running `uv sync --frozen` without the
`symbolic` optional extra, so every `tests/modules/symbolic/*` case failed
with `ModuleNotFoundError: No module named 'sympy'` and the PyPI build job
never finished. No functional changes to tools, policies, or transports
relative to 0.1.2.

### Changed
- `.github/workflows/ci.yml`: `uv sync --frozen` → `uv sync --frozen --extra symbolic` so the Python 3.12 matrix installs `sympy>=1.12` and the symbolic test suite can execute.
- `.github/workflows/publish-pypi.yml`: same extra added to the build job, unblocking the Trusted Publishing path for future releases.

### Fixed
- Repaired the release pipeline broken since CE-M4 (symbolic module) introduction: 0.1.1 and 0.1.2 CI runs had been red because the optional extra was never wired into the workflows.

[0.1.3]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.3

## [0.1.2] - 2026-04-24

Current master snapshot: 18 domains, 254 base tools, 10 admin policy-management tools, 5 transport modes.

### Added
- FB-M1 (P0 remediation): `scripts/count_tools.py` registry-backed single source for domain/tool counts; CI guard (ADR-019) gates README, `pyproject.toml`, and CHANGELOG numbers against the live REGISTRY.
- FB-M2: README subtitle "Precision Calc MCP for LLM tool use", CI/PyPI/Python/License badges, and a real `finance.npv` audit-trace sample block.
- FB-M9: GitHub About tagline aligned to "SooTool, Precision Calc MCP: Decimal-only deterministic calculation server for LLM tool use".
- `docs/architecture.md`, ADR-019 (docs-number single source) and ADR-020 (batch deterministic as_completed reordering).
- Batch regression tests covering wall-clock reduction and completion-order independence for `deterministic=True`.
- CE-M2 한국 수직 심화: realestate.kr_local_property (광역 계수), tax.kr_simplified_vat (간이과세), payroll 의료비·교육비·기부금·주택차입이자 공제 4종, 6 신규 도구 + 정책 YAML 3종.
- CE-M3 결정적 재현성 인증: 모든 응답에 `_meta.integrity`(input_hash·policy_sha256·tool_version·sootool_version·policy_source) post-processor 자동 주입. ADR-021.
- CE-M4 symbolic 하이브리드: symbolic.solve·symbolic.diff (sympy optional extra), AST 화이트리스트 + sympify locals={} 이중 경계, SIGALRM 5초 타임아웃. ADR-022.
- CE-M10 글로벌 세법 1단계 tax_us: federal_income (7 brackets × 4 filing), capital_gains (LTCG + NIIT), state_tax (CA·NY·TX), 3 신규 도구 + 정책 YAML 5종.

### Changed
- `pyproject.toml` description resynced to match README first paragraph; annotated with "keep in sync" marker (ADR-019).
- `core.batch` deterministic path now collects futures via `as_completed` and reorders by input id, shortening wall-clock to `max(item_time)` while preserving ADR-011 ordering invariant. `item_timeout_s` / `batch_timeout_s` are both enforced (ADR-020).
- README tool-catalog table reflects the updated payroll (5), tax (10), and core (8) counts; running totals aligned to the current REGISTRY.
- 도구 수 253 → 264 (base 243 → 254, admin 10 유지), 계산 도메인 16 → 18 (symbolic·tax_us 신설). 네임스페이스 18 → 20.
- `server.py` `_load_modules`: tax_us·symbolic(optional) import 추가.
- `pyproject.toml`: `[project.optional-dependencies] symbolic = ["sympy>=1.12"]` 추가.
- `scripts/count_tools.py`: `base_tools` 공식을 `total - admin_policy_tools`에서 `total - policy_tools`로 통일하여 CI guard 공식(ADR-019)과 일치. human print 라벨도 `(= 전체 - policy)`로 동기화.
- `core.pipeline.PipelineExecutor._execute`: 선언만 존재하던 `step_timeout_s`/`pipeline_timeout_s`를 `ThreadPoolExecutor(max_workers=1)` + `future.result(timeout=…)` watchdog으로 강제. 초과 시 `status="timeout"` 또는 `"skipped"`(PipelineTimeout) 응답.
- `core.batch.BatchExecutor`: `with ThreadPoolExecutor` 컨텍스트 매니저를 수동 수명 관리(`try/finally` + `shutdown(wait=False, cancel_futures=True)`)로 전환하여 `batch_timeout_s` 이후 호출측 wall-clock이 잔여 worker 완료를 기다리지 않도록 분리.
- `modules/symbolic/_bridge.run_symbolic`: 메인 스레드에서는 기존 SIGALRM 경로, 비메인 스레드(예: `core.batch` worker)에서는 `ThreadPoolExecutor(max_workers=1)` + `future.result(timeout=_EVAL_TIMEOUT_S)` watchdog으로 분기하여 `_EVAL_TIMEOUT_S` 강제.

### Fixed
- CI tool-count-guard(ADR-019) 재현 실패: `README.md` 첫 문단과 `CHANGELOG.md` [Unreleased] 요약을 live REGISTRY 수치(18 domains, 254 base tools, 10 admin policy-management tools)에 맞춰 CI grep 패턴과 정확히 정렬.

### Security
- `middleware.auth.BearerTokenValidator.validate`: 평문 `==` 비교 대신 `hmac.compare_digest`를 사용하여 Bearer 토큰 검증을 constant-time 비교로 전환. 타이밍 공격 표면 제거.

[0.1.2]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.2

## [0.1.1] - 2026-04-24

Infrastructure patch: GitHub Actions CI and PyPI Trusted Publishing workflows.
No functional changes to tools, policies, or transports.

### Added
- `.github/workflows/ci.yml`, ruff, mypy, pytest, MCP stdio smoke, `uv build` on push and pull requests
- `.github/workflows/publish-pypi.yml`, automated PyPI upload on GitHub Release publish, manual TestPyPI target via `workflow_dispatch`
- `.github/workflows/README.md`, Trusted Publishing setup guide

### Changed
- Version bump 0.1.0 → 0.1.1

[0.1.1]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.1

## [0.1.0] - 2026-04-23

Initial public release. Decimal-only calculation MCP server with 16 domains,
236 base tools, 10 admin policy-management tools, and 5 transport modes.

### Added
- Phase 1, Core kernel (M1~M4): Decimal operators, CalcTrace, REGISTRY
  auto-discovery, `core.batch` parallel executor, `core.pipeline` DAG runner
  with resume, payload guard, trace-level filter.
- Phase 1, Transports (M5): multi-transport runtime (stdio, HTTP, SSE,
  WebSocket, Unix socket) with unified hardening middleware, origin guard,
  payload size limit, per-session isolation.
- Phase 1, Skill guide (M6~M7): `sootool.skill_guide` MCP tool,
  `_meta.hints` injection pipeline, bilingual (KO+EN) playbooks and triggers
  covering tax / finance / payroll / realestate / policy-management flows.
- Phase 1, Policy management (M8): 10 admin MCP tools implementing the
  propose → activate → rollback workflow with 6-stage YAML validation,
  SHA256 integrity check, signature chain, audit log, and `policy_source` /
  `sha256` / `audit_id` trace extensions on all policy-dependent tools.
- Phase 4, Safe expression evaluator (P4-M1, ADR-017): AST-based `core.calc`
  with Decimal results, mpmath transcendentals, and explicit variable binding.
- Phase 4, Engineering domain Tier 1~3 (P4-M2~M4): 50 tools covering
  electrical, fluid, thermal, mechanical, civil, chemistry engineering, and
  SI prefix conversions.
- Phase 4, Domain Tier A (P4-M5): 25 tools across 6 domains with 6 policy
  YAML sources (capital gains, corporate, gift, inheritance, withholding,
  property tax).
- Phase 4, Domain Tier B/C (P4-M6~M7): 60 tools covering the remaining
  statistics, probability, geometry, crypto, and project-management
  surfaces plus the new `math` domain.
- Architecture Decision Records ADR-001 through ADR-017 covering kernel
  invariants, transport hardening, skill-guide contract, policy management,
  and AST calculator design.

### Fixed
- SSE legacy endpoint 307 redirect regression: normalised `/messages` and
  `/messages/` to the same handler so MCP SSE clients no longer see spurious
  redirects during initialization.
- Skill-guide playbook scenario field alignment: `scenario` keys now match
  the trigger table across KO and EN catalogues, eliminating silent lookup
  misses from bilingual clients.

### Infrastructure
- 1748 pytest cases passing, `ruff check` clean, `mypy --strict` clean within
  the documented relaxations (ADR-011).
- Five-transport end-to-end smoke tests (`scripts/mcp_smoke_*.py`) wired into
  the release checklist.
- Registry surface: 236 base tools + 10 admin policy tools = 246 tools
  exposed via `tools/list` once `sootool.policy_mgmt.tools` is imported.

[0.1.0]: https://github.com/JinHo-von-Choi/SooTool/releases/tag/v0.1.0
