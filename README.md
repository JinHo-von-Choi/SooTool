# SooTool

LLM이 확률 추론으로 산수를 틀리는 구조적 한계를 차단하는 정밀 계산 MCP 서버. Python 3.12 · FastMCP · Decimal 전용 커널 위에 16개 계산 도메인 236개 기본 도구 + admin 10개 정책 도구, 5종 전송(stdio/HTTP/SSE/WebSocket/Unix), 감사 트레이스·정책 외부화·배치·파이프라인을 얹었다.

## 왜 필요한가

LLM은 숫자를 토큰 시퀀스로 생성한다. 부가세 역산, 복리 이자, 누진세 구간, 양도소득세 장기보유특별공제, 이항분포 CDF 같은 실무 계산에서 반올림 방향·구간 경계·정책 해석이 미묘하게 어긋난다. 검증 없이 LLM 산출을 그대로 쓰면 세무 신고·재무 의사결정·의료 용량·공학 설계에서 치명적 오차가 누적된다.

문제의 층위는 두 겹이다. 첫째, 모델 자체가 산술을 수행하지 않는다. 확률 추론으로 그럴듯한 숫자를 내놓을 뿐이라 회계·세무·약제 용량 현장에서 잘못된 수치가 그대로 보고서·전표·처방에 남는다. 검증 여력이 빠듯한 전문직 실무에서는 오차 한 건이 신고 오류·환불·의료 사고로 직결된다.

둘째, 최신 대형 LLM은 내부에 계산기·Python 인터프리터를 내장하고 있지만 그 도구를 호출할지는 여전히 모델 재량이다. MCP 도구도 같은 제약을 공유한다. 구조적 한계가 단일 방어막 하나로는 닫히지 않는다는 뜻이다. SooTool은 모델 내장 도구와 독립된 두 번째 층의 MCP 서버로서 결정적 Decimal 경로, 외부화된 정책 데이터, 감사 가능한 트레이스를 제공해 방어 깊이를 늘린다. 호출 여부 자체는 AI 재량으로 남지만, 불리면 결과는 산술적으로 정확하다는 점이 보증된다.

SooTool은 그 경로를 원천 차단한다.

- Decimal 전용 커널. 입력 JSON은 `parse_float=Decimal`로 파싱되어 float이 도메인 내부로 유입되지 못한다.
- 반올림 정책 6종(HALF_EVEN · HALF_UP · DOWN · UP · FLOOR · CEIL)을 enum으로 고정하고 도구 기본값을 금지한다. 호출자가 반드시 선택한다(ADR-002).
- 세법·부동산 규제 데이터를 `src/sootool/policies/{domain}/{key}_{year}.yaml`로 외부화하고 SHA-256 무결성 검증 + lru_cache로 로드한다(ADR-009).
- 모든 응답은 `trace.{tool, formula, inputs, steps, output}` 필드를 포함한다. 계산 근거를 사용자에게 직접 보여줄 수 있다(ADR-003).
- 결정론. ThreadPool 결과는 입력 id 순으로 재정렬하고, 비결정 허용 시 `non_deterministic:true` 플래그를 강제한다(ADR-011).

## 설치

```
cd SooTool
uv sync
```

## 실행

기본(stdio, MCP 클라이언트 연동):
```
uv run python -m sootool
```

전송별 단일 기동:
```
uv run python -m sootool --transport http      --port 10535
uv run python -m sootool --transport sse-legacy --port 10536
uv run python -m sootool --transport websocket --port 10537
uv run python -m sootool --transport unix      --socket /tmp/sootool.sock
```

다중 전송 동시 기동:
```
uv run python -m sootool --transports stdio,http,websocket
```

기본 바인딩은 `127.0.0.1`. 외부 노출은 `--host 0.0.0.0` + Bearer 토큰이 의무다(ADR-014).

## Claude Code 연동

저장소 루트의 `.mcp.json`을 그대로 두면 Claude Code가 자동 인식한다. 수동 등록:
```
claude mcp add sootool -- uv run python -m sootool
```

## 도구 카탈로그 (236개 기본 + 10개 admin, 16 계산 도메인 + sootool 운영 도구)

|Namespace|Count|대표 도구|
|-|-|-|
|core|7|add, sub, mul, div, batch, pipeline, pipeline_resume|
|accounting|11|vat_extract, vat_add, balance, depreciation 3종, interest_compound 외|
|finance|15|pv, fv, npv, irr, loan_schedule, bond_ytm, bond_duration, black_scholes, var_parametric, sharpe 외|
|tax|7|progressive, kr_income, kr_withholding_simple, capital_gains_kr 외|
|realestate|8|kr_ltv, kr_dti, kr_dsr, kr_acquisition_tax, kr_transfer_tax, rental_yield 외|
|stats|14|descriptive, ttest 3종, chi_square_independence, ci_mean, regression_linear, anova, correlation 외|
|probability|30|normal/binomial/poisson, gamma, beta, exponential, lognormal, chi_square, F, bayes, factorial, nCr, nPr, expected_value|
|datetime|14|add/count_business_days, day_count, age, diff, tz_convert, solar↔lunar, solar_terms, lunar_holiday, fiscal_year, fiscal_quarter, tax_period_kr, payroll_period|
|math|10|integrate_simpson, integrate_gauss_legendre, diff_central, diff_five_point, interpolate_linear, interpolate_cubic_spline, polynomial_roots, polynomial_horner, fft, ifft|
|geometry|15|area·volume 7종, vector dot/cross/norm, matrix 4종, haversine|
|engineering|56|electrical_*, electrical_ac 11종, fluid, thermal, mechanical, structural, control 5종, si_prefix_convert|
|units|8|convert (pint), fx_convert, fx_triangulate, temperature, energy_convert, pressure_convert, data_size_convert, time_small_convert|
|medical|12|bmi, bsa, dose_weight_based, egfr, pregnancy_weeks, cha2ds2_vasc, has_bled, framingham_cvd_10y, qtc_bazett/fridericia/framingham/hodges|
|science|11|half_life, ideal_gas, molar_mass, stoichiometry, nernst, faraday_electrolysis, battery_capacity, snell_law, thin_lens, bragg, intensity|
|crypto|10|gcd, lcm, hash, is_prime, modinv, modpow, egcd, crt, euler_totient, carmichael_lambda|
|pm|5|critical_path (CPM), evm, pert, earned_schedule, monte_carlo_schedule|
|payroll|1|kr_net_monthly|
|sootool|1+10|skill_guide (항시) + policy_mgmt 10종 (admin 모드)|

전체 도구 사양은 `docs/user_guide.md` 및 `sootool.skill_guide` MCP 호출로 조회한다.

## 실전 예시

세무 체인 파이프라인. 월급 3,000,000원을 연소득으로 환산한 뒤 2026년 한국 소득세를 계산한다.
```json
{
  "name": "core.pipeline",
  "arguments": {
    "steps": [
      {"id": "annual", "tool": "core.mul",       "args": {"operands": ["3000000", "12"]}},
      {"id": "tax",    "tool": "tax.kr_income",  "args": {"taxable_income": "${annual.result.result}", "year": 2026}}
    ]
  }
}
```

재무 시나리오 비교 배치. 동일 현금흐름에 대해 할인율 3종 NPV를 동시 산출한다.
```json
{
  "name": "core.batch",
  "arguments": {
    "items": [
      {"id": "s1", "tool": "finance.npv", "args": {"rate": "0.05", "cashflows": ["-100","30","40","50"], "rounding": "HALF_EVEN", "decimals": 2}},
      {"id": "s2", "tool": "finance.npv", "args": {"rate": "0.08", "cashflows": ["-100","30","40","50"], "rounding": "HALF_EVEN", "decimals": 2}},
      {"id": "s3", "tool": "finance.npv", "args": {"rate": "0.10", "cashflows": ["-100","30","40","50"], "rounding": "HALF_EVEN", "decimals": 2}}
    ]
  }
}
```

공학 레이놀즈 수. 밀도·속도·특성길이·점성으로 층류/전이/난류 영역을 판정하고 trace에 공식을 남긴다.
```json
{
  "name": "engineering.fluid_reynolds",
  "arguments": {"density": "1000", "velocity": "2", "length": "0.05", "viscosity": "0.001"}
}
```

통계 회귀 + 신뢰구간 배치. 단일 왕복으로 선형회귀 계수·p-value와 평균 95% 신뢰구간을 동시 반환한다.
```json
{
  "name": "core.batch",
  "arguments": {
    "items": [
      {"id": "reg", "tool": "stats.regression_linear", "args": {"X": [[1],[2],[3],[4]], "y": [2.1, 4.0, 6.2, 8.1]}},
      {"id": "ci",  "tool": "stats.ci_mean",           "args": {"data": [2.1, 4.0, 6.2, 8.1], "confidence": 0.95}}
    ]
  }
}
```

## 배치와 파이프라인

- `core.batch` — N개 독립 연산을 ThreadPoolExecutor로 병렬 실행. id 중복 거부, per-item 격리(`ok|error|timeout|skipped`), 최대 500 items, per-item 10s, batch 60s 제한. 결과는 입력 id 순으로 결정적 재정렬된다(ADR-011).
- `core.pipeline` — `graphlib.TopologicalSorter` 기반 DAG 실행기. `${step_id.result.field}` 참조 문법으로 단계 간 데이터 전달. max_steps=50, max_depth=10, step_timeout_s=2.0, pipeline_timeout_s=30.0(ADR-006).
- `core.pipeline_resume` — 실패한 스텝을 TTL 10분 in-memory 캐시로부터 부분 재실행.

## 전송 지원

|Transport|용도|Flag|
|-|-|-|
|stdio|Claude Code·Desktop 기본|--transport stdio|
|http|Streamable HTTP, 권장 원격|--transport http|
|sse-legacy|2024-11 프로토콜 호환|--transport sse-legacy|
|websocket|저지연 양방향|--transport websocket|
|unix|로컬 고처리|--transport unix --socket PATH|
|multi|동시 기동|--transports stdio,http,...|

모든 HTTP 계열 전송은 Bearer 인증, `Accept-Language` 기반 로케일 감지(ko 기본), 전 도구 `_meta.hints` 자동 주입, CORS 화이트리스트를 공통 미들웨어로 적용한다(ADR-014).

## 개발

- 테스트: `make test` (pytest 1097건, 97% 커버리지)
- 린트: `make lint` (ruff)
- 타입체크: `make typecheck` (mypy)
- 포맷: `make format`
- 전송 스모크: `uv run python scripts/mcp_smoke_{stdio,http,sse,ws,unix}.py`

새 도메인 도구 추가는 `src/sootool/modules/<domain>/<tool>.py`에 `@REGISTRY.tool(namespace, name, description, version)` 데코레이터로 구현하고 도메인 `__init__.py`에서 import하면 런타임 자동 등록된다(ADR-004).

## 아키텍처

설계 결정과 근거는 `docs/architecture.md` ADR-001~017에 기록되어 있다. 핵심 invariant:

- Decimal-only 경계 · 명시적 rounding · 감사 트레이스 · 모듈 stateless / batch-safe
- 자료형 이원화: 회계·세무·금융은 전 구간 Decimal, 통계·기하·확률은 내부 float64 + 경계 Decimal 직렬화(ADR-008)
- 정책 YAML 외부화 + SHA-256 무결성(ADR-009)
- trace_level none·summary·full + SOOTOOL_MAX_PAYLOAD_KB(기본 512KB) 초과 시 trace.steps tail 절단(ADR-010)
- KRWMoney는 Decimal 상속 대신 합성(ADR-013)
- 도메인별 `*_bulk` 도구 금지, `core.batch` 일반해로 통일(ADR-006)

## 스킬 가이드

에이전트가 언제 어떤 도구를 호출해야 하는지 기술한 트리거 테이블·예시·플레이북은 `sootool.skill_guide` MCP 도구를 호출하여 조회한다. 섹션은 `triggers | examples | anti_patterns | playbooks | all`, 언어는 `ko | en`.

## 라이선스

`LICENSE` 파일 참조.
