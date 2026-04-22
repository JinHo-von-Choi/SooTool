# SooTool

LLM 정밀 계산 MCP 서버. 14개 도메인 모듈 (accounting/finance/tax/stats/datetime 완료, 그 외 계획) + Decimal 커널 + 배치/파이프라인.

## 설치

uv 설치 후:

```
cd SooTool
uv sync
```

## 실행

stdio (Claude Code 등 MCP 클라이언트 연동 기본):

```
uv run python -m sootool
```

HTTP (원격 호출):

```
uv run python -m sootool --transport http --port 10535
```

## Claude Code 연동

프로젝트 루트의 `.mcp.json`을 그대로 두면 Claude Code가 자동 인식. 수동 등록:

```bash
claude mcp add sootool -- uv run python -m sootool
```

## 도구 목록 (38개, Phase 0 + Phase 1)

### core 도구

- core.add — Decimal 정밀 덧셈 (여러 피연산자 합산)
- core.sub — Decimal 뺄셈 (a - b)
- core.mul — Decimal 곱셈 (여러 피연산자 곱)
- core.div — Decimal 나눗셈 (분모 0 예외 처리)
- core.batch — N개 독립 연산 병렬 실행
- core.pipeline — DAG 의존 연산 (${step.result.field} 참조)
- core.pipeline_resume — 파이프라인 부분 재실행

### accounting 도구

- accounting.balance — 차대변 균형 검증
- accounting.depreciation_straight_line — 정액법 감가상각
- accounting.depreciation_declining_balance — 정률법 감가상각
- accounting.depreciation_units_of_production — 생산량 비례법 감가상각
- accounting.vat_extract — 공급가·세액 역산 (gross → net + vat)
- accounting.vat_add — 세금 포함 합계 산출 (net → gross + vat)

### finance 도구

- finance.pv — 현재가치 (TVM)
- finance.fv — 미래가치 (TVM)
- finance.npv — 순현재가치
- finance.irr — 내부수익률
- finance.loan_schedule — 대출 원리금 상환 스케줄
- finance.bond_ytm — 채권 만기수익률
- finance.bond_duration — Macaulay & Modified Duration
- finance.black_scholes — Black-Scholes 유럽형 옵션 가격 + Greeks

### tax 도구

- tax.progressive — 누진세율 구간별 세액 계산
- tax.kr_income — 한국 소득세 (연도별 세율표 적용)
- tax.kr_withholding_simple — 한국 간이 원천징수
- tax.capital_gains_kr — 한국 양도소득세

### stats 도구

- stats.descriptive — 기술통계 (평균/분산/중앙값/사분위 등)
- stats.ttest_one_sample — 단일표본 t-검정
- stats.ttest_two_sample — 독립표본 t-검정
- stats.ttest_paired — 대응표본 t-검정
- stats.chi_square_independence — 카이제곱 독립성 검정
- stats.ci_mean — 평균 신뢰구간
- stats.regression_linear — 단순/다중 선형 회귀

### datetime 도구

- datetime.add_business_days — 영업일 덧셈
- datetime.count_business_days — 기간 내 영업일 수 계산
- datetime.day_count — 날짜 경과일 수 (DC/360, Actual/365 등)
- datetime.age — 생년월일 기준 나이 (년/월/일)
- datetime.diff — 두 날짜 차이
- datetime.tz_convert — 타임존 변환

## 배치 사용 예시

```json
{
  "name": "core.batch",
  "arguments": {
    "items": [
      {"id": "scenario_1", "tool": "finance.npv", "args": {"rate": "0.05", "cashflows": ["-100", "30", "40", "50"]}},
      {"id": "scenario_2", "tool": "finance.npv", "args": {"rate": "0.08", "cashflows": ["-100", "30", "40", "50"]}},
      {"id": "scenario_3", "tool": "finance.npv", "args": {"rate": "0.10", "cashflows": ["-100", "30", "40", "50"]}}
    ]
  }
}
```

## 파이프라인 사용 예시 (세무 체인)

```json
{
  "name": "core.pipeline",
  "arguments": {
    "steps": [
      {"id": "annual", "tool": "core.mul", "args": {"operands": ["3000000", "12"]}},
      {"id": "tax", "tool": "tax.kr_income", "args": {"taxable_income": "${annual.result.result}", "year": 2026}}
    ]
  }
}
```

## 개발

- 테스트: `make test`
- 린트: `make lint`
- 타입체크: `make typecheck`

## 아키텍처

`docs/architecture.md` 참조 (ADR-001~013).
