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
