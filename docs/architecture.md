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
- SooTool은 stdio와 Streamable HTTP 두 전송을 1급 지원한다. 추가 전송(HTTP+SSE legacy, WebSocket, Unix socket)은 후속 마일스톤에서 순차 추가한다.
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
