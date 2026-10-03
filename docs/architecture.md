# SooTool 아키텍처 결정 기록

## ADR-001: Decimal 의무화, float 금지
문자열 기반 Decimal 입력만 허용. float 허용 시 `allow_float=True`로 명시적 opt-in.
사유: 회계·금융에서 0.1+0.2=0.30000000000000004 유형 오류 근절.

## ADR-002: 반올림 정책 명시
모든 반올림은 `RoundingPolicy` enum으로 명시. 기본값 금지(호출자가 선택).
사유: 세무(HALF_UP)·회계(HALF_EVEN)·부가세 역산(DOWN) 등 도메인별 상이.

## ADR-003: 감사 로그 필수
모든 MCP 도구 응답은 `trace` 필드 포함(tool, formula, inputs, steps, output).
사유: 감사 추적 + 중간 계산 검증 + LLM 환각 방지.

## ADR-004: 도메인 모듈 플러그인 레지스트리
코어는 도메인 지식 없음. 모듈은 `@REGISTRY.tool`로 자동 등록.
사유: OCP 준수, 모듈 추가 시 코어 무변경.

## ADR-005: 언어 Python, 패키지 uv
수치 라이브러리 생태계(numpy/scipy/statsmodels/numpy-financial/mpmath/pint) 우위.
uv는 resolve 속도·재현성에서 우수.

## ADR-006: 배치·파이프라인 1급 지원
`core.batch`(독립 병렬)와 `core.pipeline`(DAG 의존)을 Phase 0 코어 필수 기능으로 포함.
사유:
- 문서 작성·보고서·다중 시나리오 비교 등 실사용에서 한 요청당 수십~수백 연산이 기본.
- LLM 레벨 parallel tool call(5~10개)만으로는 호출당 프레이밍 토큰 누적으로 비경제적.
- 항목별 trace 독립성·per-item timeout·max items 제한으로 감사성과 안정성 동시 확보.
결정 세부:
- 실행기: `ThreadPoolExecutor` 기본(산수 대부분 µs급, GIL 영향 미미). 무거운 numpy 경로는 자동 GIL 릴리스.
- 안전: per-item 10s, per-batch 60s, max 500 items 기본. id 중복 reject.
- 파이프라인 참조 문법: `${step_id.result.필드경로}`. 순환 감지는 `graphlib.TopologicalSorter`.
- 의존 실패 전파: 파이프라인에서 선행 step 실패 시 후행은 `status="skipped"`.
- 도메인 레벨 `*_bulk` 도구는 원칙적으로 만들지 않음. 일반해 `core.batch`로 충분.

## ADR-007: 도메인 모듈 배치 호환성 의무
모든 도메인 MCP 도구는 `core.batch`/`core.pipeline`으로 호출되어도 상태 공유 없이 독립 실행되어야 한다.
사유: 스레드풀 재진입 시 모듈 전역 상태로 인한 결과 오염 방지.
결정:
- 모듈 내부에 가변 전역 변수 금지. 불변 상수와 함수형 인터페이스만 허용.
- 외부 리소스(환율 캐시 등)는 `threading.Lock`으로 보호 또는 read-only snapshot 사용.
- 모듈 수용 기준에 "N=100 병렬 호출 시 결과 동일성" 테스트 필수 포함.

## ADR-008: 자료형 이원화 프로토콜
회계/세무/금융은 Decimal 전 구간, 통계/기하/확률은 내부 float64 + 경계 Decimal 직렬화, 옵션/큰 수는 mpmath.
사유: Decimal을 numpy/scipy에 주입 시 C-level 최적화 무력화 및 메모리 파편화. 영역별 최적 자료형 사용이 성능과 정확성의 파레토 프런티어.
결정:
- `core/cast.py`가 경계 변환을 단일 관리(decimal_to_float64, float64_to_decimal_str, mpmath_to_decimal).
- 각 모듈 README에 "내부 자료형 및 캐스팅 정책" 섹션 의무.
- 서버 JSON 파싱은 `parse_float=Decimal`로 입구 누수 차단.

## ADR-009: 정책 데이터 외부화
세법·부동산 규제 등 가변 데이터는 Python 코드에서 분리, `src/sootool/policies/{domain}/{year}.yaml`에 수록.
사유: 2026년 세율 2027년 적용 같은 '정밀한 오답' 방지. 감사 추적·롤백·재현성 확보.
결정:
- YAML 전면에 `sha256`, `effective_date`, `notice_no`, `source_url` 필수 헤더.
- 로더는 파일 SHA256 검증 후 메모리 캐시(불변).
- 모든 정책 호출 도구는 `year` 필수, 응답 trace에 `policy_version` 포함.
- 지원 연도 외 호출은 `UnsupportedPolicyError`.
- 외부 신뢰 API 래핑은 거부(네트워크 의존성, 테스트 재현성 상실).

## ADR-010: Trace Leveling + 페이로드 상한
기본 응답은 summary, 상세는 opt-in. 페이로드 상한으로 MCP 통신 실패 방지.
사유: batch 500개 full trace는 수 MB에 도달하여 MCP 메시지 크기 제한 초과.
결정:
- `trace_level: none | summary | full` (기본 `summary`).
  - `none`: result만
  - `summary`: inputs, output, formula (steps 생략)
  - `full`: 전체 steps 포함
- 환경변수 `SOOTOOL_MAX_PAYLOAD_KB=512` 초과 시 tail 절단 + `truncated: true` 플래그.
- 배치 응답은 per-item `trace_level` override 지원.

## ADR-011: Determinism 기본값
동일 입력 → 동일 출력 보장을 1급 원칙으로 강제.
사유: 금융/세무에서 비결정성은 신뢰성 붕괴. 회계 감사·법적 증빙 불가.
결정:
- `deterministic=True` 기본값. 명시 해제 시에만 비결정 연산 허용.
- 난수는 `np.random.default_rng(seed=0)` 사용. 전역 난수 상태 금지.
- `ThreadPoolExecutor` 결과는 입력 id 순으로 재정렬 후 반환.
- 부동소수 누적 순서에 민감한 연산은 `numpy.kahan_sum` 또는 Decimal 경로 선택.
- 비결정 허용 시 응답에 `non_deterministic: true` 플래그 의무.

## ADR-012: MCP 도구 스키마 버전 관리
LLM 프롬프트에 박제된 도구 스키마의 진화 경로 명시.
사유: 배포 후 Breaking Change는 에이전트 다수 실패 유발. Soft Deprecation으로 전환 기간 확보.
결정:
- 각 도구 메타데이터에 `version: "MAJOR.MINOR.PATCH"` 포함.
- Breaking Change 시 응답에 `deprecated: {since, replacement, sunset_date}` 추가, 6개월 유예.
- 인자 스키마 확장은 새 필드를 optional로 추가하는 방식만 허용. 기존 필드 타입 변경 금지.
- 레지스트리 시작 시 deprecated 도구 목록 로그 출력.

## ADR-013: KRWMoney 합성(Composition over Inheritance)
원화 처리용 통화 클래스는 Decimal 상속이 아닌 합성으로 구현.
사유: `Decimal.__mul__` 등 연산 결과가 부모 타입으로 다운캐스팅되어 `rounding` 정책 손실(LSP 위반).
결정:
- `KRWMoney(amount: Decimal, rounding: RoundingPolicy = DOWN, unit: int = 1)`. `unit=10`이면 10원 단위 반올림.
- 연산자 오버로딩(`__add__`, `__sub__`, `__mul__`)은 결과에 동일 `rounding`, `unit` 전파.
- 복합 연산 누적 오차 테스트(합산 후 절삭 vs 절삭 후 합산) 필수.
- 원화 외 통화는 ISO 4217 소수점 규칙 기반 별도 클래스 추후 추가 가능.

## ADR-014: 다중 전송 계층 지원

결정:
- SooTool은 stdio와 Streamable HTTP 두 전송을 1급 지원한다. 추가 전송(HTTP+SSE legacy, Unix socket)은 후속 마일스톤에서 순차 추가한다. WebSocket 전송은 ADR-025 에서 제거했다.
- 전송 계층은 `src/sootool/transports/` 패키지로 격리된다. REGISTRY는 전송 계층을 인식하지 않는다.
- 기본 네트워크 바인딩은 loopback(`127.0.0.1`). 외부 노출(`--host 0.0.0.0`)은 명시적 opt-in이며, `SOOTOOL_AUTH_TOKEN` 또는 `--auth-token` 미설정 시 기동을 거부한다.
- Streamable HTTP는 Starlette 미들웨어 체인(RequestID → Logging → Auth → CORS)으로 감싼 ASGI 앱으로 노출한다.
- 인증은 "nullable 검증기 리스트" 구조(`list[TokenValidator]`)로 작성하여 mTLS/OAuth2를 미들웨어 추가만으로 확장 가능하게 한다.
- 다중 전송 동시 기동은 `asyncio.gather`로 오케스트레이션한다. 단일 REGISTRY 인스턴스를 공유하며 런타임에 불변이다.
- `/healthz` 헬스체크 엔드포인트는 인증 없이 `{"status":"ok","tools":<int>,"version":"<pep621>","uptime_s":<int>}`를 반환한다.
- stdio와 HTTP를 동시 기동할 때는 systemd/supervisor 구동임을 경고 로그로 안내한다.

사유:
- MCP 클라이언트 생태계가 스펙 버전별·구현별로 전송 요구가 갈라지며, 단일 전송 제공은 통합 비용을 사용자에게 전가한다.
- 단일 REGISTRY 공유로 구현 복잡도가 `O(전송 수) + O(1)(공통 미들웨어)`로 억제된다.
- 기본 loopback + 인증 필수 정책은 무인증 공용 노출 위험을 제거한다.

## ADR-015: 에이전트 능동 활용 가이드

결정:
- SooTool 서버는 `sootool.skill_guide` MCP 도구로 트리거·예시·안티패턴·플레이북을 JSON으로 노출한다.
- FastMCP `instructions` 필드에 도구 우선 사용 지시를 주입한다.
- 모든 도구 응답이 `_meta.hints` 배열을 포함하며 세션 호출 이력을 근거로 후속 행동을 제안한다.
- `.github/skills/sootool/SKILL.md` 및 통합 스니펫 3종(Claude Code / Cursor / AGENTS.md)을 배포한다.
- 가이드 데이터는 SemVer(`version` 필드)로 관리하며 ADR-012 변경 규칙 준수한다.
- 세션 상태는 `SessionStore` 프로토콜 + `InMemoryStore` 구현으로 추상화하여 Redis drop-in 가능하게 한다.
- `_meta.hints` 주입은 6개 규칙 기반(세무 trace 미완, 반복 산술, 구 정책 연도, trace 절단, 수동 체인, 과도 단일 호출).
- result와 trace는 변경 없이 `_meta`에만 기록하여 ADR-011 결정론 훼손을 방지한다.

사유:
- 도구 등록만으로는 LLM이 확률 추론 대신 도구 호출 경로로 자동 전환하지 않음.
- Memento(AnchorMind) MCP가 동일 문제에 대해 검증한 패턴(instructions + guide 도구 + _meta.hints + 스킬 문서 + 사용자 스니펫) 재사용.
- 서버 측 단일 근원으로 가이드를 유지해 트리거·플레이북 개정 시 전 에이전트가 자동 최신화.

## ADR-016: 정책 파일 사용자 관리

결정:
- 정책 YAML을 이중 저장소로 분리: 패키지 동봉 기본값(읽기 전용) + 사용자 덮어쓰기(XDG_DATA_HOME 또는 `SOOTOOL_POLICY_DIR`).
- 로더는 덮어쓰기 > 기본값 순으로 해석하며, 호출자에게 `policy_source` 로 어느 저장소가 적용됐는지 투명하게 반환한다.
- 쓰기 도구 10종(`sootool.policy_*` — validate, propose, activate, rollback, history, diff, list, export, import, status)은 admin 모드 한정으로 노출한다. 진입은 환경변수 `SOOTOOL_ADMIN_MODE=1` 또는 CLI `--admin` 중 하나.
- 모든 쓰기는 원자적 파일 교체(tmp → rename) + JSONL 감사 로그(append-only)로 기록한다. audit_id 는 계산 도구 trace 에 `policy_audit_id` 로 전파된다.
- 수명 주기: draft → validate → propose → activate (24시간 TTL). rollback 은 activate 역연산으로 감사 로그에 기록한다.
- 계산 도구 trace 는 `policy_source: package|override`, `policy_sha256`, `policy_audit_id` 3개 필드를 의무 주입하여 덮어쓰기 여부를 호출자가 항상 식별 가능하게 한다.
- 번들 서명 검증은 기본 비활성(`require_signature`), 민감 도메인은 `SOOTOOL_POLICY_REQUIRE_SIGNATURE=1` 으로 강제 가능하다.
- 전년도 대비 민감도 임계값은 `SOOTOOL_POLICY_DIFF_THRESHOLD`(기본 50%p) 또는 호출 인자 `sensitivity_threshold` 로 제어한다.
- ADR-009 원칙(SHA256 검증·year 필수·외부 API 금지·감사 추적)은 모두 유지한다.

사유:
- 세법·부동산 규제는 매년 개정되지만 편집→커밋→배포 루프가 비개발자 사용자를 배제하여 실무 투입 리드 타임을 분기 단위로 지연시킨다.
- 코드 저장소 변경 없이 정책만 갱신 가능해야 실무 투입 리드 타임이 당일로 단축된다.
- YAML 직접 편집은 스키마·교차 검증 실패가 런타임까지 전파되므로 서버 측 검증 파이프라인(validate → propose → activate)의 의무화가 필요하다.
- 감사 가능성(누가·언제·어떤 고시문으로 바꿨는가)은 회계·세무 자동화의 법적 요구사항이며 JSONL append-only 로그로 충족한다.

## ADR-017: core.calc 보안 경계

결정:
- `core.calc` 도구는 Python `eval`/`exec`/`compile` 을 사용하지 않는다. `ast.parse(mode="eval")` 로 구문 트리를 얻고 전용 NodeVisitor 로 화이트리스트에 포함된 노드·연산자·함수·상수만 통과시킨다.
- 허용 AST 노드: `Expression`, `BinOp`, `UnaryOp`, `Constant`(int/float), `Name`, `Call`, `Tuple`(Call 인자 위치에서만), `Load`. 허용 연산자: `Add, Sub, Mult, Div, Pow, Mod, FloorDiv, USub, UAdd`. 허용 함수: `sqrt, abs, floor, ceil, round, log, log10, log2, ln, exp, sin, cos, tan, asin, acos, atan, atan2, pow`. 허용 상수: `pi, e, tau`. 그 외(Attribute/Subscript/Lambda/Comprehension/BoolOp/Compare/IfExp/NamedExpr/JoinedStr/Starred/List/Set/Dict/Await/Yield)는 명시 차단하고 에러 메시지에 노드 종류와 위치를 포함한다.
- 수치 평가는 이원화한다. 순수 정수 사칙·모듈러·정수 지수 `Pow` 는 Decimal 직접 연산으로, 초월 함수와 비정수 지수 `Pow` 는 `mpmath.workdps(precision)` 로 격리된 컨텍스트에서 계산한 뒤 `core.cast.mpmath_to_decimal` 을 통해 Decimal 문자열로 복귀한다(ADR-008 유지).
- 변수 바인딩은 호출자 제공 `dict[str, str]` 만 사용한다. 전역·빌트인·클래스 속성 참조는 AST 수준에서 불가능하다. 미정의 이름은 `UndefinedVariableError`, 파싱 실패는 `InvalidExpressionError`, 화이트리스트 위반은 `DisallowedOperationError`, 복잡도 초과는 `ExpressionTooComplexError` 로 분류한다. 0 나눗셈·모듈러 0·도메인 위반은 `DomainConstraintError` 로 통합한다.
- 복잡도 상한은 AST 노드 300개, 표현식 문자열 3000자를 기본값으로 고정하고 `SOOTOOL_CALC_MAX_NODES`, `SOOTOOL_CALC_MAX_EXPR_LEN` 환경변수로만 조정 가능하다. 허용 함수·노드·상수 집합 확장은 별도 PR 과 보안 리뷰를 거친다.

사유:
- `eval` 기반 계산기는 prompt injection·supply-chain 공격 경로에서 임의 코드 실행 표면이 넓다. LLM 경유 호출에서 악의적 입력이 `expression` 인자에 직접 주입될 수 있다. AST 화이트리스트는 허용 노드를 명시적으로 관리하므로 감사 가능하고, 확장 시 코드 리뷰에서 즉시 식별된다.
- Decimal/mpmath 이원화는 ADR-001(Decimal 전 구간) 및 ADR-008(초월 함수 mpmath 경유) 과 일치하며 트레이스의 출력 타입을 문자열 하나로 통일해 ADR-003(트레이스 의무) 을 지킨다.
- 복잡도 상한을 보수적으로 고정하면 catastrophic parsing DoS (`(((...)))` 중첩, 초장문 Pow 체인) 를 상수 시간에 차단하면서 일반적인 수식 길이에는 영향이 없다.

## ADR-019: 배포 문서 숫자 단일 소스

결정:
- 도구 수·계산 도메인 수·운영 네임스페이스 수·정책 도구 수·admin 정책 도구 수는 REGISTRY 전수 조회 결과(`scripts/count_tools.py`)를 유일한 진실로 한다.
- 배포 문서 3자 — `README.md` 첫 문단·도구 카탈로그 헤더, `pyproject.toml` `project.description`, `CHANGELOG.md` 릴리즈 요약 — 는 동일 숫자 문자열을 노출한다. `pyproject.toml` description 상단에 `# keep in sync with README first paragraph` 주석을 유지한다.
- 계산 도메인의 정의는 "운영 네임스페이스(`core`, `sootool`) 를 제외한 모든 네임스페이스" 로 고정한다. 전체 네임스페이스·계산 도메인·운영 도메인은 분리 표기하여 혼동을 차단한다.
- CI 가드는 `scripts/count_tools.py --json` 출력을 기준으로 README·pyproject·CHANGELOG 의 선언 숫자 토큰을 정규식으로 대조하고, `--assert-total`/`--assert-domains`/`--assert-policy` 단언을 병행한다. 불일치 시 빌드 실패로 릴리즈 태깅·PyPI 배포를 차단한다.
- 테스트 수는 `pytest --collect-only` 결과를 부가 지표로 기록하되 빌드 차단 기준은 아니다(테스트는 지속 추가되며 문서 동기화 우선순위가 낮다).

사유:
- 문서 간 숫자 불일치는 "Decimal 정밀성" 이라는 제품 약속과 직접 충돌한다. 첫인상에서 신뢰가 꺾이면 후속 엔지니어링 성과가 상쇄된다.
- 수동 동기화는 사람 개입마다 드리프트가 재발한다. REGISTRY 를 단일 소스로 삼고 CI 에서 기계적으로 대조하면 릴리즈 이전에 오차가 발견되며, 배포 후 사후 패치(0.1.1 hotfix) 필요성을 제거한다.
- `core`·`sootool` 을 계산 도메인에서 분리하는 것은 외부 사용자 관점의 "계산 능력" 정의와 내부 아키텍처의 "운영 표면" 정의를 충돌 없이 유지하기 위한 결정이다.

### Appendix — base_tools 공식 규범 (2026-04-24)

`scripts/count_tools.py`가 보고하는 `base_tools`는 다음 공식으로 고정한다.

```
base_tools = total_tools − policy_tools
```

policy_tools 는 `sootool` 네임스페이스에서 `policy_` 접두어를 갖는 10개 도구의 합계(read-only 6 + admin-gated 4). admin_policy_tools 는 policy_tools 의 서브셋이며 `_require_admin()`을 호출하는 4개 도구(policy_propose·policy_activate·policy_rollback·policy_import)로 별도 집계한다.

CI(`.github/workflows/ci.yml`의 Tool count single source guard step)는 REGISTRY 실측 total·policy·admin 값을 계산한 뒤 README·pyproject·CHANGELOG 선언 문자열과 일치하는지 grep 4종 + `--assert-total`·`--assert-base`·`--assert-domains`·`--assert-policy`·`--assert-admin` 5종 단언을 모두 통과시켜야 한다.

이 규범을 변경하려면 ADR-019 개정이 선행되어야 한다.

## ADR-020: core.batch deterministic 재정렬 전략

결정:
- `BatchExecutor.run(deterministic=True)` 경로의 결과 수집 루프를 순차 `future.result()` 블록킹 방식에서 `concurrent.futures.as_completed` 기반 수집 + 입력 id 순 재정렬로 전환한다.
- ADR-011 결정론 invariant(응답 `results` 배열이 입력 `items` 의 id 순서) 를 유지하되, wall-clock 은 `max(item_time)` 에 근접하도록 단축한다. 느린 선행 항목이 뒤따르는 빠른 항목의 결과 수집을 블로킹하지 않는다.
- `item_timeout_s` 와 `batch_timeout_s` 두 시한을 모두 존중한다. 개별 future 의 제출 시각(`item_started_at`) 을 저장하고, 루프 매 반복에서 `now - item_started_at >= item_timeout_s` 인 future 를 즉시 타임아웃 처리한다. 총 경과가 `batch_timeout_s` 를 초과하면 남은 pending 전체를 타임아웃으로 일괄 종결한다.
- `deterministic=False` 경로는 이전과 동일하게 완료 순서로 노출하고 응답에 `non_deterministic=True` 플래그를 강제한다. 두 경로 모두 `as_completed` 를 공유하므로 코드 중복을 제거한다.

사유:
- 기존 순차 `future.result()` 루프는 ThreadPoolExecutor 의 병렬 제출 이점을 수집 단계에서 희석했다. 예를 들어 50개 항목 중 첫 항목만 5초 소요·나머지 49개는 0.1초인 배치에서, 기존 구조는 첫 항목 완료까지 5초 블로킹 후에야 뒤쪽 이미 완료된 항목들을 수집했다. 새 구조는 빠른 항목들을 완료 즉시 수집하므로 동일 배치의 wall-clock 이 `max(item_time)` 수준으로 수렴한다.
- ADR-011 의 결정론 약속은 응답 `results` 의 인덱스 순서에만 의존한다. 수집 순서를 변경해도 최종 재정렬 단계에서 입력 id 순으로 복원하면 invariant 는 보존된다. 회귀 테스트 `test_batch_deterministic_order_independent_of_completion` 이 이 성질을 감시한다.
- `item_timeout_s` 를 루프 내 명시적 polling 으로 처리하면 개별 항목의 취소 가능성을 유지하면서도 `as_completed` 의 timeout 파라미터(배치 단위) 와 충돌하지 않는다. 추가적인 회귀 테스트 `test_batch_deterministic_wall_clock_bounded_by_max_item` 이 느린 선행 항목 시나리오에서 wall-clock 상한을 감시한다.

## ADR-021: 결정적 재현성 인증 필드 (_meta.integrity)

결정:
- 모든 도구 응답에 `_meta.integrity` 블록을 자동 주입한다. 필드는 `input_hash`(canonical JSON sha256), `tool_version`, `sootool_version` 을 필수로 하고 정책을 실제로 소비한 호출에 한해 `policy_sha256`, `policy_source` (`<domain>/<name>/<year>` 형식) 를 추가한다.
- Canonical JSON 은 `sort_keys=True`, `separators=(",", ":")` 규칙을 고정한다. Decimal 은 기존 `CalcTrace` 정규화 규칙(str 변환) 을 그대로 재사용하여 트레이스와 해시가 동일한 표현을 공유한다.
- `REGISTRY.invoke` 진입 시 kwargs 를 스레드 로컬 컨텍스트에 스택 방식으로 저장·복원한다. `core.batch`·`core.pipeline` 처럼 invoke 를 중첩 호출하는 도구의 개별 결과도 동일 post-processor 경로에서 integrity 가 주입되며, 외부 프레임의 inputs/policy 가 복원되어 상호 간섭이 없다.
- 정책 사용 감지는 `sootool.policy_mgmt.loader.load` 말미에서 `set_policy_meta(source, sha256, domain, key, year)` 을 호출해 스레드 로컬에 기록하는 훅으로 구현한다. 정책 비사용 도구(`core.*`, `finance.*` 중 정책 미참조 도구 등) 는 `policy_sha256` / `policy_source` 필드를 방출하지 않는다.
- `_meta.integrity` 는 항상 `result` / `trace` 를 건드리지 않고 `_meta` 하위에만 추가한다. `_meta.hints` 와 공존하며, integrity post-processor 는 기존 `_meta` 에 병합되도록 구현해 다른 meta 블록을 훼손하지 않는다.
- `sootool_version` 은 `importlib.metadata.version("sootool")` 을 프로세스 단위로 캐시한다. 패키지 미설치 개발 환경에서는 `0.0.0+unknown` 샌티넬을 반환하여 테스트와 smoke 실행을 방해하지 않는다.

사유:
- 트레이스 단독으로는 "같은 입력·같은 정책" 인지 확인하려면 inputs 필드를 수작업으로 재해시해야 했다. 해시를 도구 응답 자체에 포함시키면 LLM·사용자·회계 감사 절차 모두가 한 줄 비교로 재현성을 검증할 수 있다.
- 정책 YAML 의 sha256 은 이미 `trace_ext.enrich_response` 가 top-level 과 trace 양쪽에 노출하고 있지만, 입력 해시가 누락되면 "동일 정책·다른 입력" 과 "동일 정책·동일 입력" 을 구분할 수 없다. `_meta.integrity` 블록이 두 축을 한 곳에 묶어 감사 로그로서의 가치를 높인다.
- Key 순서 독립적 해시는 JSON 기반 MCP 프로토콜의 직렬화 순서가 클라이언트마다 달라도 동일한 재현성을 보장한다. `sort_keys=True` 는 canonical 규칙 중 가장 단순하면서 해시 충돌 공간을 늘리지 않는다.
- 스레드 로컬 컨텍스트 방식을 택한 이유는 (1) 도구 함수 시그니처를 수정하지 않아도 되고 (2) 기존 post-processor 체인과 호환되며 (3) `core.batch` 병렬 실행에서도 각 워커 스레드가 독립된 프레임을 가질 수 있기 때문이다. 동일 스레드 내 중첩 invoke 는 stack-style save/restore 로 분리하여 외부 프레임이 내부 호출 이후에도 올바른 input_hash 를 계산할 수 있도록 보존한다.
- `_meta` 병합 구현은 `_hints_post_processor` 가 `_meta` 존재 시 early-return 하는 기존 계약을 존중한다. integrity 는 hints 이후 실행되어 `_meta.hints` 와 `_meta.integrity` 가 공존하고, trace 엔리치로 이미 policy 메타를 주입한 도구(`tax.kr_income` 등) 도 추가 충돌 없이 integrity 블록을 갖는다.

## ADR-022: symbolic 하이브리드 경계 (CE-M4)

결정:
- 신규 네임스페이스 `symbolic` 에 `symbolic.solve`·`symbolic.diff` 두 도구만 노출한다. 범위는 "기호 풀이·기호 미분 후 Decimal 재평가 브릿지" 로 제한하며, LaTeX 출력·적분·급수 전개 등 sympy 의 다른 표면은 본 ADR 범위 외(향후 별도 ADR 로만 확장) 이다.
- 의존성 `sympy>=1.12` 는 기본 의존이 아닌 optional extra `[symbolic]` 로 선언한다. `uv pip install -e '.[symbolic]'` 또는 `uv sync --extra symbolic` 으로 활성화한다. sympy 미설치 환경에서 도구 호출 시 `SymbolicDependencyError` 로 친절한 설치 안내를 반환하고, 다른 도구 경로는 영향 없이 동작한다. 기본 배포 용량을 보존하기 위한 설계다.
- 입력 수식(`equation` / `expression`) 은 sympy.sympify 에 도달하기 전에 `core.calc._parse` + `core.calc._count_and_validate` 를 통과한다. AST 화이트리스트(ADR-017 재사용) 가 `__import__`·`eval`·`exec`·`compile`·`open`·`Lambda`·`Attribute`·`Subscript`·`Comprehension`·`Starred`·`List`·`Set`·`Dict` 를 포함한 위험 노드를 1차 차단한다. sympify 호출은 `locals={}`, `rational=False` 고정으로 이름 해석 경로를 봉쇄한다.
- 수치 경계는 ADR-001/008 을 승계한다. sympy 결과는 `evalf(50)` → `sympy.Float` → `mpmath.mpf` → `core.cast.mpmath_to_decimal` → Decimal 문자열. 중간에 Python `float` 타입을 경유하지 않는다. 유리수 해(`sympy.Rational`) 는 분자·분모를 정수로 꺼낸 뒤 Decimal 나눗셈으로 표현한다. 복소·기호 잔류 해는 `solutions` 배열에서 제외하고 `symbolic` 배열에만 문자열로 담는다.
- 복잡도 상한은 expression 문자열 5000자(core.calc 3000자 기본보다 다소 넉넉하게 잡되 DoS 방어 수준 유지), AST 노드 한도는 core.calc 기본 300(환경변수 `SOOTOOL_CALC_MAX_NODES` 로 조정) 을 그대로 사용, sympy 평가 자체는 `signal.SIGALRM` 기반 5초 타임아웃으로 래핑한다. 타임아웃은 `DomainConstraintError` 로 변환하여 트레이스에 남긴다. SIGALRM 미지원 환경(Windows·비메인 스레드) 에서는 보호 없이 실행되며 이는 plan 의 Linux/POSIX 서버 타겟 제약을 반영한다.
- 모든 응답에 `result`/`symbolic`/`trace` 세 축을 유지한다. `symbolic.solve` 는 `{solutions: [...], symbolic: ["x = ...", ...], trace}`, `symbolic.diff` 는 `{derivative: "...", numeric: "..." | null, trace}` 형식으로 고정한다. trace 는 CalcTrace 포맷으로 inputs·steps·output 을 채워 ADR-003(트레이스 의무) 을 지킨다.

사유:
- "sympy 래퍼는 고도 기호 엔진 대체 불가" 라는 외부 비판(A축 검토 기록) 을 수용하여, 본 마일스톤은 정책적 기호 풀이가 아닌 "기호 단계를 거쳐 Decimal 을 복구하는 브릿지" 로 범위를 조인다. 두 도구만 노출하는 것은 트레이스·정책 서명·재현성 계약을 유지 가능한 최소 표면이다.
- AST 화이트리스트를 sympy 앞에 세우는 것은 sympify 단독으로는 임의 코드 실행 경로(예: `x.__class__.__base__.__subclasses__()`) 가 Python 객체 그래프를 통해 노출될 수 있기 때문이다. core.calc 의 화이트리스트를 재사용하면 허용 문법을 한 곳에서 감사할 수 있고, 확장 시 ADR-017 과 동일한 리뷰 절차를 따르게 된다.
- optional extra 는 기본 배포의 용량·의존성 공격 표면을 보존하기 위함이다. sympy 는 내부적으로 mpmath 를 공유하지만(이미 기본 의존) sympy 자체의 순수 Python 패키지 크기와 릴리즈 주기가 기본 의존군과 다르다. opt-in 경로는 세무·금융 사용자가 기호 연산 비사용 시 불필요한 업데이트 노이즈를 피하게 한다.
- evalf → mpf → Decimal 경로는 Phase 1 부터 지켜 온 "float 누수 금지" 원칙의 연장이다. sympy.Float 객체를 str 로 전환한 뒤 mpmath 컨텍스트(50자리) 에서 재파싱하면, Python float 의 IEEE-754 반올림이 트레이스 경계에 끼어들지 않는다.
- 타임아웃을 SIGALRM 으로 도입한 이유는 sympy.solve 가 입력에 따라 비선형 시간으로 폭발할 수 있기 때문이다. 5초 상한은 일반적인 방정식·다항식·단순 초월 방정식에는 충분하고, 초과 시 사용자에게 "복잡한 symbolic 연산은 정책적 도메인 도구(tax.*, finance.*) 를 사용하라" 는 방향성을 강제한다.

## ADR-023: Release Gate, Timeout Contracts, Optional Extras Matrix

컨텍스트:
0.1.1~0.1.2 릴리스 기간 동안 세 종류의 구조적 갭이 누적됐다.

1. 릴리스 게이트 부재: CE-M4 이후 CI 가 `uv sync --frozen` 에 `--extra symbolic` 누락으로 만성 red 였으나, master push 와 tag push 를 가로막는 상태 체크가 없어 CI red 상태에서 두 차례 릴리스가 진행됐다. 0.1.2 는 publish 빌드 잡에서 같은 이유로 실패하여 PyPI 업로드가 스킵됐다.
2. 시간 축 제어의 선언-실장 갭: `BatchExecutor.batch_timeout_s`/`item_timeout_s`, `PipelineExecutor.step_timeout_s`/`pipeline_timeout_s`, `symbolic/_bridge._EVAL_TIMEOUT_S` 네 시간 계약이 필드·상수로 선언되었으나 실행 경로에서 실제 wall-clock 을 구속하지 않았다. 2067개 기존 테스트는 값·순서 불변만 검증하고 시간 축 계약은 검증하지 않았다.
3. Optional Extras 설치 매트릭스 공백: `symbolic` extra 가 optional 임에도 기본 설치(`uv sync --frozen`) 에서 symbolic 테스트가 어떻게 처리되는지 CI 가 검증하지 않았다. 따라서 "extra 없이도 sootool 이 import 가능한가" 라는 필수 계약이 회귀로 깨져도 감지되지 않았다.

결정:

R1. 릴리스 게이트 (Release Gate)
- master 브랜치에 GitHub branch protection rule "Require status checks to pass before merging" 을 활성화하고 필수 status check 로 `Test (Python 3.12 / extras=none)`, `Test (Python 3.12 / extras=symbolic)`, `Test (Python 3.12 / extras=all)` 세 개를 지정한다.
- 로컬 릴리스 프로세스의 사전 조건으로 `make release-preflight` 를 둔다. `scripts/release_preflight.py` 가 stdlib `urllib.request` 로 GitHub API 를 호출하여 현재 master commit 의 CI run `conclusion` 이 `"success"` 일 때만 exit 0 을 반환한다.
- 릴리스 절차는 `docs/release.md` 에 명문화된다.

R2. 시간 축 계약 (Timeout Contracts)
- 다음 계약은 `tests/core/test_timeout_contracts.py` 의 7 테스트 케이스로 실제 wall-clock 구속을 증명해야 한다.
  - `BatchExecutor.batch_timeout_s` — batch 수준 wall-clock 상한.
  - `BatchExecutor.item_timeout_s` — 개별 아이템 wall-clock 상한.
  - `PipelineExecutor.step_timeout_s` — step 수준 wall-clock 상한.
  - `PipelineExecutor.pipeline_timeout_s` — 파이프라인 수준 wall-clock 상한(초과 시 후속 step 은 `status="skipped"` + `error.type="PipelineTimeout"`).
  - `symbolic/_bridge._EVAL_TIMEOUT_S` — 메인 스레드 SIGALRM 경로와 비메인 스레드 `ThreadPoolExecutor` watchdog 경로 양쪽에서 강제.
- 실행 계약 변경이 필요하면 해당 테스트 파일의 tolerance(`SOOTOOL_TIMEOUT_TOLERANCE`) 와 본 ADR 을 함께 개정한다.

R3. Optional Extras 매트릭스 (Optional Extras Matrix)
- `pyproject.toml` `[project.optional-dependencies]` 에 `all = ["sootool[symbolic]"]` 메타 extra 를 유지한다. 새 extra 가 추가되면 `all` 에 누적된다.
- `.github/workflows/ci.yml` matrix 를 `extras: ["none", "symbolic", "all"]` 3종으로 확장하여 각 조합에서 전체 pytest 스위트가 pass 해야 한다.
- `import sootool` 과 `from sootool.server import _load_modules; _load_modules()` 는 sympy 설치 없이도 성공해야 한다 (`extras=none` 매트릭스가 이 계약을 방어).
- `tests/modules/symbolic/test_*.py` 는 상단에 `pytest.importorskip("sympy")` 를 두어 extras=none 환경에서 자동 스킵되도록 한다.

결과:
- R1·R2·R3 가 성립하면 (가) CI red 위 릴리스 재발 방지, (나) timeout 관련 리팩터의 회귀 방어, (다) Optional extra 회귀의 CI 즉시 감지가 확보된다.
- 개발자 동선: 시간 계약을 바꾸면 `test_timeout_contracts.py` 도 바꾸고 본 ADR 을 개정한다. Optional extra 를 추가하면 `all` 에도 추가하고 매트릭스를 갱신한다. 릴리스 전 `make release-preflight` 가 선행된다.

상태: 수용됨(Accepted). 2026-04-24.

관련 아티팩트:
- 플랜: `docs/plans/2026-04-24-release-quality-improvements.md`
- 구현 커밋: 본 ADR 과 함께 반영되는 릴리스 품질 개선 PR
- 테스트: `tests/core/test_timeout_contracts.py`
- 스크립트: `scripts/release_preflight.py`, `scripts/count_tools.py`(`--assert-base` 포함)
- 워크플로: `.github/workflows/ci.yml` (extras matrix), `.github/workflows/publish-pypi.yml` (attestation)


## ADR-024: 계산 영수증과 재실행 검증

- 영수증은 응답의 `_meta.integrity` 블록이다. ADR-021 필드에 `tool`(정규화된 도구 이름)과 `result_hash`를 더한다. `result_hash` 는 응답 본문(result, trace 등)의 canonical JSON sha256 이며 모든 중첩 수준의 `_meta` 를 제외한다. `_meta` 에는 세션 통계와 힌트처럼 호출 이력에 따라 달라지는 값이 들어가므로 해시에 넣지 않는다.
- `input_hash` 는 도구 시그니처의 기본값을 채운 정규화 입력으로 계산한다. 직접 호출, MCP 호출, `sootool.call` 호출이 같은 해시를 갖는다.
- `sootool.verify_receipt(tool, arguments, receipt)` 는 같은 도구를 다시 실행해 `tool`, `input_hash`, `result_hash`, `tool_version`, `policy_sha256` 을 대조한다. `sootool_version` 차이는 경고로만 보고한다. 결정적 엔진이라 가능한 검증이며 외부 API 에 의존하는 계산기는 제공할 수 없다.
- 재실행 검증 제외 대상: `core.batch`, `core.pipeline`, `core.pipeline_resume`(결과에 소요 시간과 실행 id 포함), 쓰기 도구, `sootool.verify_receipt` 자신.
- 선택 서명: 환경변수 `SOOTOOL_RECEIPT_KEY_FILE` 이 가리키는 파일의 base64 ed25519 개인 키로 `signature` 를 제외한 스탬프의 정규화 JSON 에 서명하고 `key_id`(공개 키 sha256 앞 16자)를 함께 싣는다. 키는 파일 경로로만 참조하며 도구 인자로 받지 않는다. 키를 읽을 수 없으면 계산 결과는 그대로 반환하고 `signature_error` 코드를 남긴다.
- 서명 기반 함수는 `sootool.core.signing` 에 두고 정책 번들 서명(`policy_mgmt.signatures`)과 공유한다.
- 벽시계 시각은 영수증에 넣지 않는다(결정성 유지). 시각이 필요한 감사 기록은 별도 로그 계층의 책임이다.
- 정확도 등급: 응답 `_meta.engine` 은 도구가 사용하는 수치 엔진(`decimal`, `mpmath`, `float64`, `composite`, `none`)을 알린다. 정의 모듈의 임포트를 정적으로 분석하는 보수적 분류(`core/engines.py`)이며 영수증 해시에는 포함하지 않는다. `float64` 는 IEEE 754 배정밀도 근사임을 뜻한다.

상태: 제안됨(Proposed). 2026-10-03.

관련 아티팩트:
- 구현: `src/sootool/core/audit.py`, `src/sootool/core/receipts.py`, `src/sootool/core/signing.py`, `src/sootool/receipt_tools.py`
- 테스트: `tests/core/test_receipts.py`
- 계획: `docs/plans/2026-10-03-enhancement-roadmap.md` 4.1


## ADR-025: MCP SDK v2 이행, 무상태 전환, 오류 계약

배경: MCP 2026-07-28 사양은 프로토콜 세션과 initialize 핸드셰이크를 없애 모든 요청을 독립으로 만들었고, Python SDK v2 가 이를 지원하며 v1 은 보안 수정만 받는다. SDK v2 는 WebSocket 서버 전송을 제거했고 HTTP+SSE 는 사양에서 폐기됐다.

결정:
- `mcp>=2.3,<3` 으로 이행한다. 서버 클래스는 `MCPServer` 이며 도구 어노테이션 필드는 snake_case 다. v1 은 지원하지 않는다.
- 요청 컨텍스트(`core/request_context.py`): 네트워크 전송의 미들웨어(`RequestContextMiddleware`)가 요청마다 로케일(Accept-Language), 무상태 표식, 인증 범위를 contextvar 로 설정하고 요청이 끝나면 복원한다. 호출 이력(세션)은 stdio 와 프로세스 내 호출에서만 유지한다. 무상태 요청은 이력이 필요한 힌트 규칙(연속 호출 감지 등)을 건너뛰고 `_meta.session_stats` 를 싣지 않는다. `SOOTOOL_SESSION_ID` 환경변수와 세션 저장소의 로케일 상태는 제거했다. Accept-Language 는 이제 `sootool.skill_guide` 의 로케일 해석에 실제로 반영된다.
- 전송: WebSocket 제거. HTTP+SSE 는 SDK 의 `sse_app` 으로 단순화하고 폐기 경고를 남기며 다음 마이너에서 제거한다. Unix 소켓은 맞춤 프레이밍 대신 UDS 위의 Streamable HTTP 로 서비스한다(소켓 파일은 요청 권한으로 바인드 시점부터 생성, Host 헤더 제한 없음, 접근 통제는 파일 권한). 이는 기존 Unix 소켓 클라이언트에 비호환 변경이다. Streamable HTTP 는 `stateless_http=True` 로 서비스한다.
- 쓰기 도구 노출 분리: 정책 쓰기 도구(4종)는 로컬 전송(stdio, unix)에만 노출한다. 네트워크 전송에 노출하려면 `--admin --remote-admin --admin-token` 이 모두 필요하다. 인증은 범위를 갖는다: `SOOTOOL_AUTH_TOKEN` 은 `read`, `SOOTOOL_ADMIN_TOKEN` 은 `read` 와 `policy-write`. 관리자 게이트(`_is_admin`)는 관리자 모드 환경변수와 요청의 `policy-write` 범위를 모두 요구한다. 범위가 부여되지 않은 요청은 출처로 갈린다: 로컬 호출(stdio, 프로세스 내)은 모든 범위를 갖고, 네트워크 요청은 아무 범위도 갖지 않는다(`has_scope`). 파일 권한으로 접근을 통제하는 Unix 소켓은 `LocalTrustMiddleware` 가 모든 범위를 명시적으로 부여한다. 토큰을 구성하지 않은 HTTP 서버는 쓰기 도구가 노출되어 있어도 쓰기를 수행하지 못한다.
- 오류 계약(`boundary.py`, `core/errors.py`): 모든 도구 오류를 `{"error": {"code", "message", "retryable", "field"?, "details"?}}` 구조의 `isError` 결과로 돌려준다. 오류 클래스마다 고유한 `code` 를 갖는다. SDK 단계에서 거부되는 경우(알 수 없는 도구, 필수 인자 누락, 타입 오류)도 `SooToolServer` 가 같은 형식으로 변환하며 거부된 입력값은 되돌려주지 않는다. 선언되지 않은 인자는 SDK 가 조용히 버리므로 거부한다(오타 난 선택 인자가 무시되어 기본값으로 계산되는 일을 막는다). 예기치 못한 예외는 `internal_error` 로 변환하고 상세는 로그에만 남긴다. `D()` 가 비숫자 입력에 날 `decimal.InvalidOperation` 대신 `InvalidNumberError`, 0 나눗셈에 `DivisionByZeroError` 를 낸다(표준 예외도 함께 상속해 호환).
- 입력: 문자열 숫자 파라미터는 JSON 숫자도 받는다. 부동소수는 클라이언트가 보낸 배정밀도 값의 최단 왕복 표기로 변환한다. 입력 스키마는 string 으로 광고한다.

결과: 네트워크 전송이 라운드 로빈 로드 밸런서 뒤에서 동작하고, 요청 사이에 상태가 새지 않으며, 클라이언트가 오류를 코드로 분기할 수 있다.

상태: 제안됨(Proposed). 2026-10-03.

관련 아티팩트:
- 구현: `src/sootool/boundary.py`, `src/sootool/core/request_context.py`, `src/sootool/core/errors.py`, `src/sootool/transports/`, `src/sootool/middleware/`
- 테스트: `tests/core/test_boundary.py`, `tests/core/test_request_context.py`, `tests/transports/test_http_e2e.py`, `tests/middleware/`
- 계획: `docs/plans/2026-10-03-enhancement-roadmap.md` A4, A5, A6, B1, B4


## ADR-026: 시점·조문 인지 정책 엔진 (schema v2)

배경: 정책 YAML 은 연도별 한 파일이라 연중 개정(같은 해의 시행일이 다른 두 버전)과 국회 확정 전 개정안을 표현하지 못했고, 근거 조문은 자유 문자열(`notice_no`)뿐이었다.

결정:
- 헤더 v2(모두 선택, 하위 호환): `effective_to`, `status`(enacted, proposed, superseded), `version`, `citations`(law, article?, url?, note?), `reviewed_by`. 같은 연도의 추가 버전은 `<name>_<year>@<시행일>.yaml` 이다.
- 호출 단위 해석: 정책 기반 도구(`policy=True` 로 선언한 27개와 `policy_get`, `policy_export`)는 공통 인자 `as_of`(YYYY-MM-DD)와 `include_proposed` 를 받는다. 레지스트리가 이 인자를 도구 함수에 넘기지 않고 호출 범위의 컨텍스트(`core/policy_context.py`)로 설정한다. 도구 함수의 시그니처는 바꾸지 않는다. 중첩 호출(위임 도구, batch, pipeline)은 컨텍스트를 상속하며 batch·pipeline 의 워커 스레드로는 호출마다 컨텍스트를 복사해 전달한다.
- 선택 규칙(`policy_mgmt/loader.py`): 시점이 없으면 확정 버전 중 시행일이 가장 늦은 것(호출 시각에 의존하지 않아 결정적). `as_of` 가 있으면 시행 기간에 시점이 속하는 버전 중 시행일이 가장 늦은 것이며 교체된 버전도 자기 기간에는 쓰인다. 개정안은 `include_proposed` 일 때만 후보다. 후보가 없으면 `policy_not_in_effect`(시행 기간 목록 포함) 또는 `policy_not_enacted` 를 낸다.
- 표기: 결과에 `policy_status`, `policy_effective_date`, `policy_effective_to`, `policy_citations` 를 싣고 `_meta.integrity` 에 `policy_status`, `policy_effective_from`, `policy_effective_to` 를 더한다. 개정안으로 계산한 결과에는 `proposed_policy_in_use` 힌트가 붙는다. `as_of` 와 `include_proposed` 는 영수증 입력 해시에 포함되어 재실행 검증이 같은 버전으로 재현된다.
- 관리: 검증은 헤더 v2 필드 형식과 같은 연도 확정 버전의 시행 기간 겹침을 확인한다. 활성화는 시행일이 같으면 교체, 다르면 새 버전 파일을 만든다. 롤백은 `effective_date` 로 버전을 고른다.
- 자체 해시 갱신과 검사는 `scripts/policy_stamp.py` 가 맡고 CI 가 `--check` 로 검사한다.

상태: 제안됨(Proposed). 2026-10-03.

관련 아티팩트:
- 구현: `src/sootool/policy_mgmt/loader.py`, `src/sootool/core/policy_context.py`, `src/sootool/core/registry.py`, `src/sootool/policy_mgmt/validators.py`, `src/sootool/policy_mgmt/tools.py`
- 테스트: `tests/policy_mgmt/test_policy_versions.py`, `tests/policy_mgmt/test_policy_schema_v2.py`, `tests/core/test_policy_tools.py`
- 문서: `docs/policy_management.md`
- 계획: `docs/plans/2026-10-03-enhancement-roadmap.md` 4.2


## ADR-027: 명령줄 인터페이스와 공유 레지스트리

결정:
- 서브커맨드 체계(`call`, `tools`, `batch`, `pipeline`, `receipt`, `policy`, `skill-guide`, `version`)를 `src/sootool/cli/` 에 둔다. 서브커맨드가 없거나 `serve` 이면 서버로 기동하며 기존 서버 플래그는 그대로다.
- 모든 도구 호출은 `REGISTRY.invoke` 단일 경로를 거친다. 인자 검증은 MCP 경계와 같은 규칙을 쓴다(`cli/binder.py`: `boundary._coercible` 기반 숫자 허용, 같은 `invalid_arguments` 오류 계약). 숫자 문자열은 변환하지 않고 그대로 전달한다.
- 쓰기 도구(`policy propose|activate|rollback|import`와 `call` 로 호출한 쓰기 도구)는 CLI 에서 관리자 모드를 먼저 확인하고(종료 코드 3), 레지스트리의 관리자 게이트를 다시 통과한다(이중 게이트). CLI 는 로컬 신뢰 컨텍스트라 요청 범위 검사를 하지 않는다.
- 종료 코드: 0 성공, 1 도구 오류, 2 입력 오류, 3 관리자 모드 필요, 70 내부 오류. 오류는 표준에러에 오류 계약 JSON 으로 낸다.
- 의존성을 늘리지 않는다: 대화형 REPL(prompt_toolkit)과 셸 자동완성(argcomplete)은 도입하지 않는다. 인자는 `--arg 이름=값` 반복과 `--arg-json` 으로 받으며 CSV 간편 입력은 두지 않는다(엄격한 JSON 유지). 설정 파일은 두지 않는다.

상태: 제안됨(Proposed). 2026-10-03.

관련 아티팩트:
- 구현: `src/sootool/cli/`, `src/sootool/__main__.py`
- 테스트: `tests/cli/test_cli.py`
- 계획: `docs/plans/2026-04-24-cli-subcommand-support.md`, `docs/plans/2026-10-03-enhancement-roadmap.md` D6
