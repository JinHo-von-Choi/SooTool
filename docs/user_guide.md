# 사용자 가이드

SooTool 도구를 부를 때 알아야 할 공통 규칙과 도메인별 도구 구성을 정리한다. 도구 하나하나의 인자는 `sootool tools describe <도구>`(CLI), `sootool.describe`(MCP), [tool_catalog.md](tool_catalog.md)에서 확인한다.

## 도구 찾기

```bash
sootool tools list --search 종부세          # 줄임말, 일상 표현, 영어 동의어로 검색
sootool tools list --domain payroll         # 네임스페이스 안의 도구 목록
sootool tools describe payroll.kr_salary    # 인자, 기본값, 정책 인자, 정확도 등급
```

MCP에서는 `sootool.search(query)`와 `sootool.describe(name)`이 같은 역할을 한다. 이 두 도구는 `--profile lean`에서 노출된다.

## 공통 규칙

### 숫자는 문자열로 넘긴다

금액, 비율, 측정값은 `"50000000"`, `"0.035"`처럼 문자열로 넘긴다. 쉼표, 단위, 공백은 넣지 않는다. JSON 숫자를 넘겨도 받지만 부동소수(`0.1` 등)는 배정밀도 최단 표기로 바뀌며, 그 사실이 응답의 `_meta.input_coerced`에 기록된다. 배정밀도를 넘는 자릿수가 필요하면 처음부터 문자열로 넘긴다. `year`, `periods`처럼 정수로 선언된 인자는 정수로 넘긴다.

응답의 숫자도 모두 문자열이다.

### 정책 도구: year, as_of, include_proposed

세율, 공제액, 보험료율 같은 법정 값을 쓰는 도구 43개는 정책 파일을 읽는다(카탈로그의 `정책` 열이 `예`인 도구).

|인자|뜻|
|-|-|
|`year`|귀속 연도. 정책 도구는 대부분 필수다. 지원하지 않는 연도면 오류를 낸다.|
|`as_of`|`YYYY-MM-DD`. 그날 시행 중이던 버전으로 계산한다. 연중에 값이 바뀌는 4대보험, 간이세액표에서 쓴다.|
|`include_proposed`|`true`면 국회 확정 전 개정안(`status: proposed`)도 후보에 넣는다. 기본은 `false`다.|

`as_of`를 생략하면 그 연도 확정 버전 중 시행일이 가장 늦은 것을 쓴다. 호출 시각에 따라 결과가 바뀌지 않는다. 응답에는 적용한 버전의 `policy_effective_date`, `policy_effective_to`, `policy_status`, `policy_citations`(근거 조문), `policy_sha256`이 붙는다.

### 반올림

반올림 관행이 상황마다 갈리는 금융·회계 도구는 `rounding`과 `decimals`를 받는다.

|값|동작|대표 용도|
|-|-|-|
|`HALF_EVEN`|0.5는 짝수 쪽으로|회계 일반, 금융 지표|
|`HALF_UP`|0.5는 올림|일상 반올림|
|`DOWN`|0 쪽으로 버림|부가세 역산(원 단위 절사)|
|`UP`|0에서 먼 쪽으로 올림||
|`FLOOR`|음의 무한대 쪽으로||
|`CEIL`|양의 무한대 쪽으로||

세목별 끝수 처리를 법령이 정한 경우(지방세 10원 미만 절사, 건강보험료 10원 미만 절사 등) 도구가 그 규칙을 적용하며, 도구 설명에 규칙이 적혀 있다.

### trace 분량

`core.add`, `core.sub`, `core.mul`, `core.div`, `core.calc`는 `trace_level`을 받는다. `summary`(기본)는 공식·입력·출력, `full`은 중간 단계까지, `none`은 결과만 담는다. 응답이 `SOOTOOL_MAX_PAYLOAD_KB`(기본 512KB)를 넘으면 `trace.steps`를 뒤에서부터 잘라내고 `truncated: true`를 표시한다.

### 오류

도구 오류는 다음 구조로 돌아온다. MCP에서는 `isError` 결과, CLI에서는 표준에러 JSON, SDK에서는 `SooToolError` 예외(`to_payload()`가 같은 구조)다.

```json
{"error": {"code": "policy_not_in_effect", "message": "...", "retryable": false, "field": "as_of", "details": {...}}}
```

|code|뜻|
|-|-|
|`invalid_arguments`|선언되지 않은 인자, 필수 인자 누락, 타입 불일치|
|`invalid_input`, `invalid_number`|값이 형식에 맞지 않음|
|`unknown_tool`|없는 도구 이름|
|`domain_constraint`|값의 범위 위반(음수 금액, 특이행렬 등)|
|`division_by_zero`|0으로 나눔|
|`input_limit`|입력 크기 한도 초과|
|`policy_not_in_effect`|`as_of` 시점에 시행 중인 버전이 없음. `details`에 시행 기간 목록이 온다.|
|`policy_not_enacted`|그 연도에 개정안만 있음. `include_proposed=true`로 다시 부를 수 있다.|
|`policy_unavailable`, `policy_integrity`|정책 파일이 없거나 해시가 맞지 않음|
|`invalid_expression`, `disallowed_operation`, `undefined_variable`, `expression_too_complex`|`core.calc` 수식 오류|
|`no_sign_change`|`core.solve_for` 탐색 구간에 해가 없음|
|`timeout`|시간 제한 초과|
|`internal_error`|예기치 못한 오류. 상세는 서버 로그에만 남는다.|

선언되지 않은 인자는 무시하지 않고 거부한다. 오타 난 선택 인자가 조용히 기본값으로 계산되는 일을 막기 위해서다.

### 입력 한도

지나치게 큰 입력은 계산 전에 `input_limit`로 거부한다. 기본값은 다음과 같고 `SOOTOOL_LIMIT_<이름>` 환경변수로 바꾼다.

|이름|기본값|적용 대상|
|-|-|-|
|`ARG_STRING_CHARS`|100,000|문자열 인자 길이|
|`ARG_LIST_ITEMS`|100,000|목록·객체 원소 수|
|`ARG_DEPTH`|16|중첩 깊이|
|`MATRIX_DIM`|200|행렬 한 변|
|`POLYNOMIAL_DEGREE`|256|다항식 차수|
|`FFT_SAMPLES`|65,536|FFT 표본 수|
|`LOAN_MONTHS`|1,200|대출 상환 개월 수|
|`MONTE_CARLO_TRIALS`|1,000,000|몬테카를로 시행 횟수|
|`BOOTSTRAP_RESAMPLES`|100,000|부트스트랩 재표본 수|
|`COMBINATORICS_N`|20,000|factorial, nCr, nPr의 n|
|`CRYPTO_DIGITS`|2,048|crypto 정수 자릿수|
|`BUSINESS_DAYS_SPAN`|100,000|영업일 계산 구간(일)|
|`SCENARIOS`|50|`core.compare` 시나리오 수|

### 응답의 `_meta`

|필드|내용|
|-|-|
|`integrity`|영수증. `tool`, `input_hash`, `result_hash`, `tool_version`, `sootool_version`, 정책 도구는 `policy_sha256` 등.|
|`engine`|계산 엔진. `decimal`, `mpmath`, `float64`(근사), `composite`, `none`.|
|`hints`|다음에 쓸 만한 도구 제안. 세무 계산의 trace 생략, 같은 산술 반복, 지난 연도 정책, trace 잘림, 수동 체인, 단일 호출 남발을 감지한다.|
|`input_coerced`|부동소수 인자를 문자열로 바꾼 기록|
|`deprecated`|폐기 예고된 도구를 불렀을 때 대체 도구와 제거 예정 버전|
|`session_stats`|호출 횟수. stdio와 프로세스 내 호출에서만 붙는다.|

`_meta`는 결과 값에 영향을 주지 않으며 영수증의 `result_hash` 계산에서도 빠진다.

## 도메인별 구성

|네임스페이스|도구 수|다루는 계산|
|-|-|-|
|core|11|Decimal 사칙연산, 수식 계산(`calc`), 병렬 실행(`batch`), 단계 연결(`pipeline`, `pipeline_resume`), 역산(`solve_for`), 시나리오 비교(`compare`), 계산 설명(`explain`)|
|accounting|11|부가세 가산·역산, 차대변 검증, 감가상각 3종(정액·정률·생산량비례), 손익계산서, 영업활동현금흐름, 재무비율, DuPont 분해|
|tax|17|소득세 기본세율, 종합소득세 신고 흐름, 근로소득 간이세액표, 양도소득세, 증여세, 상속세, 법인세, 간이과세 부가세, 근로장려금, 증권거래세, 연금소득세, 자동차세, 등록면허세, 지방소득세·지방교육세·농어촌특별세, 범용 누진세|
|tax_us|4|미국 연방 소득세, 자본이득세, 주 소득세(CA, NY, TX), FICA(자영업자 SECA 포함)|
|payroll|15|월급 실수령액(4대보험·소득세·지방소득세), 세후에서 세전 역산, 시급 환산, 퇴직금, 연말정산, 상여 세액, 의료비·교육비·기부금·주택자금 공제, 연장·야간·휴일 수당, 주휴수당, 최저임금 확인, 국민연금 수령액, 소득월액보험료|
|realestate|10|취득세, 양도소득세, 재산세, 종합부동산세, 광역별 지방세, LTV, DTI, DSR, 임대수익률, 청약 가점|
|finance|18|PV, FV, NPV, IRR, ROI, CAGR, 투자회수기간, 대출 상환표, 채권 YTM·듀레이션, 블랙-숄즈와 그릭스, 선도·선물 가격, 옵션 손익, VaR(역사적·모수적), 샤프·소르티노 비율|
|stats|14|기술통계, t-검정 3종, 분산분석, 크루스칼-월리스, 만-휘트니 U, 윌콕슨, 카이제곱 독립성, 평균 신뢰구간, 부트스트랩 신뢰구간, 선형회귀, 효과크기(Cohen's d, η²)|
|probability|30|정규·이항·포아송·지수·감마·베타·로그정규·카이제곱·F 분포의 pdf(pmf)·cdf·ppf, 베이즈, 기댓값, 계승, 조합, 순열|
|datetime|14|날짜 차이, 만 나이, 영업일 가감·계산(한국 공휴일), 이자 일수 관행(30/360, ACT/365 등), 시간대 변환, 음양력 변환, 24절기, 명절, 회계연도·분기, 소득세 과세기간, 급여 정산 기간|
|math|10|심프슨·가우스-르장드르 적분, 중앙차분·5점 미분, 선형·3차 스플라인 보간, 다항식 근·호너 평가, FFT, IFFT|
|geometry|15|넓이·부피, 벡터 내적·외적·노름, 행렬 곱·행렬식·역행렬·연립방정식, 하버사인 거리|
|engineering|56|옴의 법칙, 전력, 저항·커패시터·인덕터 합성, 교류 임피던스, 3상 전력, 역률 보정, RC 필터, 테브난·노턴 등가, 유체(레이놀즈, 베르누이, 다르시-바이스바흐), 열전달, 응력·변형·좌굴, 기어, 베어링 수명, 제어 응답, 신뢰도|
|units|8|물리 단위 변환, 환전(직접·삼각), 온도, 에너지, 압력, 데이터 크기, 짧은 시간 단위|
|medical|12|BMI, 체표면적, eGFR, 체중 기반 투약량, 임신 주수, CHA₂DS₂-VASc, HAS-BLED, 프레이밍햄 10년 심혈관 위험, QTc 4종|
|science|11|반감기, 이상기체, 몰질량, 화학량론, 네른스트 식, 패러데이 전기분해, 배터리 용량, 스넬 법칙, 얇은 렌즈, 브래그 법칙, 빛의 세기|
|crypto|10|최대공약수, 최소공배수, 확장 유클리드, 모듈러 역원·거듭제곱, 중국인의 나머지 정리, 소수 판별, 오일러 피, 카마이클 람다, 해시|
|pm|5|임계 경로(CPM), PERT, 획득가치(EVM), 획득일정, 몬테카를로 일정 시뮬레이션|
|symbolic|2|방정식 풀이, 미분. 결과를 Decimal로 다시 평가한다. `pip install "sootool[symbolic]"`이 필요하다.|
|sootool|12|에이전트 가이드(`skill_guide`), 영수증 검증(`verify_receipt`), 정책 관리 10종|

`engineering`과 `probability`는 도구를 더 늘리지 않는다. 기존 도구의 버그 수정은 계속한다.

## 정책 관리 도구

|도구|권한|하는 일|
|-|-|-|
|`sootool.policy_list`|읽기|정책 목록과 적용 저장소(패키지 기본값, 사용자 덮어쓰기)|
|`sootool.policy_get`|읽기|정책 본문 조회(`as_of`, `include_proposed` 지원)|
|`sootool.policy_history`|읽기|변경 감사 기록|
|`sootool.policy_diff`|읽기|두 버전의 차이|
|`sootool.policy_validate`|읽기|YAML 검증만 하고 저장하지 않음|
|`sootool.policy_export`|읽기|이식용 번들 생성(선택적 서명)|
|`sootool.policy_propose`|쓰기|초안 생성과 검증|
|`sootool.policy_activate`|쓰기|초안을 덮어쓰기 저장소에 반영|
|`sootool.policy_rollback`|쓰기|덮어쓰기를 지워 패키지 기본값으로 복귀|
|`sootool.policy_import`|쓰기|번들 가져오기|

쓰기 도구는 관리자 모드(`SOOTOOL_ADMIN_MODE=1` 또는 `--admin`)에서만 동작한다. 절차는 [policy_management.md](policy_management.md)를 본다.
