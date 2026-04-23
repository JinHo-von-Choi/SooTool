# SooTool User Guide

작성자 최진호. 작성일 2026-04-23. 버전 0.1.0.

본 문서는 SooTool이 노출하는 도구 표면을 도메인별로 요약한다. 상세한 입력
스키마와 trace 예시는 `sootool.skill_guide` MCP 호출 또는 개별 테스트 케이스
(`tests/modules/<domain>/`)를 참조한다. 정책 관리와 admin 워크플로우는
`docs/policy_management.md`를, 아키텍처 결정은 `docs/architecture.md`를 본다.

## 총괄

SooTool 0.1.0은 15개 계산 도메인에 236개의 기본 도구를 노출하고, 별도의 10개
admin 정책 도구를 `sootool` 네임스페이스에 올린다. admin 도구는
`SOOTOOL_ADMIN_MODE=1` 환경변수에서만 호출이 허용되며, 등록 자체는 항상
이뤄진다. `sootool.skill_guide` 1개를 포함하면 `tools/list`는 총 246개를
반환한다.

| 네임스페이스 | 도구 수 | 대표 도구 | 설명 |
|-|-|-|-|
| core | 8 | core.add, core.batch, core.pipeline, core.calc | Decimal 4칙, DAG 파이프라인, AST 수식 평가기 |
| accounting | 11 | accounting.balance, accounting.vat_add, accounting.depreciation_straight_line | 회계식·감가상각·부가세 |
| tax | 7 | tax.kr_income, tax.capital_gains_kr, tax.progressive | 한국 세목 누진세 + 범용 누진세 |
| payroll | 1 | payroll.kr_salary | 2026 4대보험+소득세 통합 급여 계산 |
| realestate | 8 | realestate.kr_acquisition_tax, realestate.kr_dsr, realestate.kr_comprehensive | 취득·종부세·DSR/LTV/DTI·임대수익률 |
| finance | 15 | finance.npv, finance.irr, finance.black_scholes, finance.var_historical | 현금흐름·옵션·채권·리스크 지표 |
| probability | 30 | probability.normal_cdf, probability.poisson_pmf, probability.beta_ppf | 이산/연속 분포 pdf/cdf/ppf + 조합 |
| stats | 14 | stats.ttest_two_sample, stats.anova_oneway, stats.regression_linear | 가설 검정·분산분석·회귀 |
| datetime | 14 | datetime.diff, datetime.tax_period_kr, datetime.lunar_to_solar | 영업일·회계연도·음양력 변환 |
| geometry | 15 | geometry.haversine, geometry.matrix_solve, geometry.vector_norm | 면적·부피·행렬·벡터 |
| engineering | 56 | engineering.electrical_ohm, engineering.darcy_weisbach, engineering.lmtd | 전기·유체·열·기계·제어·신뢰성 |
| science | 11 | science.ideal_gas, science.nernst, science.half_life | 화학·전기화학·광학·방사능 |
| medical | 12 | medical.bmi, medical.egfr, medical.cha2ds2_vasc | 임상 점수·신기능·심혈관 위험 |
| pm | 5 | pm.critical_path, pm.evm, pm.monte_carlo_schedule | 일정·수행가치·몬테카를로 |
| crypto | 10 | crypto.gcd, crypto.modpow, crypto.is_prime, crypto.crt | 정수론·해시·합동 |
| units | 8 | units.convert, units.fx_convert, units.temperature | 단위·통화·온도 변환 |
| math | 10 | math.integrate_simpson, math.fft, math.polynomial_roots | 수치 적분·미분·FFT·보간 |
| sootool | 11 | sootool.skill_guide, sootool.policy_list, sootool.policy_propose | skill 가이드 + admin 정책 도구 10개 |

## 공통 규약

- 숫자 인자는 모두 Decimal 문자열로 주입한다. float 리터럴을 직접 전달하면
  ADR-004 float 누수 금지 정책에 위배된다.
- 모든 도구는 `trace_level` 인자 (`none` / `summary` / `full`)를 지원하고, 응답은
  `{result, trace}` 구조를 유지한다.
- 응답 크기가 `SOOTOOL_MAX_PAYLOAD_KB`(기본 512KB)를 초과하면 trace.steps가
  꼬리부터 잘리고 `truncated: true`가 실린다.
- 한국 세목·부동산 도구는 `year` 인자를 필수 요구하며, 내부적으로
  `src/sootool/policies/<domain>/<file>.yaml`의 버전을 SHA256으로 검증한 뒤
  로드한다.

## 도메인별 상세

### core
Decimal 4칙(`add/sub/mul/div`)과 병렬 실행기(`batch`), DAG 파이프라인
(`pipeline`, `pipeline_resume`), AST 기반 수식 평가기(`calc`, ADR-017)를
제공한다. LLM이 산술을 직접 수행하면 안 되는 모든 경로의 대체 출구다.

### accounting
재무상태표(`balance`), 손익계산서(`income_statement`), 영업활동현금흐름
(`cashflow_operating`), 감가상각 3종(정액·정률·생산량비례), 부가세 가산/추출,
DuPont 3·5요소, 비율 분석을 포함한다.

### tax / payroll
- `tax.kr_income`, `tax.capital_gains_kr`, `tax.kr_corporate`,
  `tax.kr_gift`, `tax.kr_inheritance`, `tax.kr_withholding_simple`은 정책
  YAML 기반 2026 한국 세목.
- `tax.progressive`는 범용 누진세 엔진.
- `payroll.kr_salary`는 4대보험 + 소득세 + 지방소득세를 하나의 trace로 합성.

### realestate
취득세, 양도세, 종합부동산세, 재산세, DSR/DTI/LTV, 임대수익률을 제공한다.
모든 도구는 2026년 정책 YAML을 참조하며 `policy_source`와 `sha256`을 trace에
기록한다.

### finance
현재가치/미래가치, 내부수익률, 순현재가치, 대출상환 스케줄, Black-Scholes,
Bond YTM·Duration, Forward/Futures 가격, 옵션 페이오프, Historical/Parametric
VaR, Sharpe/Sortino ratio를 포함한다.

### probability / stats
`probability.*`는 정규/이항/포아송/지수/감마/베타/카이제곱/F/로그정규
분포의 pdf/cdf/ppf 및 조합·기댓값·베이즈를 제공한다. `stats.*`는 t-검정
3종(일표본·독립·대응), 분산분석(ANOVA/Kruskal-Wallis), 회귀, 카이제곱
독립성, Mann-Whitney U, Wilcoxon, 부트스트랩 CI, 효과크기(Cohen's d,
η²)를 포함한다.

### datetime
날짜 차이, 영업일 가감산, 한국 회계연도·세무기간 추출, 음양력 변환, 24절기
조회, 급여 기간 분리 도구를 제공한다. 공휴일 데이터베이스는 `holidays` +
`workalendar` 이중 소스로 검증된다.

### geometry / engineering / science / medical / pm / crypto / units / math
각 도메인은 대표 도구 예시를 통해 역할이 설명된다. 정확한 파라미터는
`sootool.skill_guide` 호출 시 반환되는 playbook에 명시되고, 전체 인자
스펙은 `REGISTRY.list()`의 각 엔트리 `fn.__doc__` 또는 대응 테스트에서
확인한다.

### sootool (skill + admin)
- `sootool.skill_guide`는 일반 사용자용이다.
- `policy_list`, `policy_get`, `policy_diff`, `policy_history`, `policy_export`,
  `policy_import`, `policy_validate`, `policy_propose`, `policy_activate`,
  `policy_rollback` 10개는 admin 전용이며 `SOOTOOL_ADMIN_MODE=1` 환경에서만
  실행된다. 상세 워크플로우는 `docs/policy_management.md` 참조.

## 다음 단계

- 트리거 테이블과 한국어/영어 playbook은 `sootool.skill_guide()` 호출로
  직접 조회한다.
- 아키텍처와 ADR-001~017은 `docs/architecture.md`를 본다.
- 정책 편집·배포 절차는 `docs/policy_management.md`를 본다.
- 전송 모드별 스모크 스크립트는 `scripts/mcp_smoke_*.py`를 본다.
