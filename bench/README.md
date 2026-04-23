# SooTool 벤치마크 리트머스 (FB-M3)

작성자: 최진호
작성일: 2026-04-24
실행 버전: v0.1.x

## 목적

외부 평가자 피드백 "왜 필요한가?" 에 대한 정량적 증빙. 한국 소득세·부가세·복리이자·
확률 분포·공학 AC 회로·양도소득세 등 20 케이스에서 LLM 직접 계산과 SooTool
Decimal 정답을 비교하여 정확도 차이를 공개한다.

이 디렉토리는 CI 에서 실행하지 않는다. 로컬에서 수동 실행용이며 LLM API 비용이
발생한다. 결과는 `results/YYYY-MM-DD.md` 로 누적된다.

## 구성

```
bench/
  __init__.py
  cases.yaml          # 20 케이스 입력·기대값
  run_benchmark.py    # LLM 호출 + REGISTRY.invoke 비교 실행기
  README.md           # (본 파일)
  results/
    template.md       # 결과 출력 스켈레톤
    .gitkeep
```

## 20 케이스 개요

| 카테고리 | 수 | 내용 |
|-|-|-|
| tax_korea | 8 | 소득세 구간 경계·내부: 14M / 50M / 88M / 125M / 150M / 300M / 500M / 1B |
| vat | 3 | 부가세 역산 DOWN / HALF_UP / HALF_EVEN (정책별 원단위 차이 유도) |
| finance_compound | 2 | 월복리 120개월, 일복리 30일 FV |
| probability | 2 | 이항 CDF n=30 k=15, 정규 PPF q=0.999 |
| stats | 1 | 일표본 양측 t-검정 p-value |
| engineering_ac | 2 | RLC 직렬 임피던스, 3상 균형 전력 P |
| tax_korea_capgain | 2 | 양도소득세 장특공 10년·15년 일반 부동산 |

`cases.yaml` 의 각 케이스는 `id`, `prompt`, `tool_call`(SooTool 호출 규격),
`expected_decimal_string`, `category`, `difficulty` 필드를 가진다. 기대값은
master@587b763 기준 `REGISTRY.invoke` 출력으로 산출된 Decimal 문자열이다.

## 사용법

### 1. 사전 준비

API 키 환경변수 (없는 LLM 은 자동 skip):

```
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

모델 오버라이드(선택):

```
export SOOTOOL_BENCH_OPENAI_MODEL="gpt-4o"
export SOOTOOL_BENCH_ANTHROPIC_MODEL="claude-3-7-sonnet-latest"
export SOOTOOL_BENCH_GOOGLE_MODEL="gemini-2.5-pro"
```

SDK 설치 (프로젝트 의존성에는 포함되지 않음):

```
uv pip install openai anthropic google-genai
```

### 2. 실행

LLM 전체 비교:

```
uv run python bench/run_benchmark.py
```

결과 파일 지정:

```
uv run python bench/run_benchmark.py --out bench/results/my-run.md
```

SooTool ground truth 만 기록 (LLM 호출 생략, 비용 0):

```
uv run python bench/run_benchmark.py --skip-llm
```

### 3. 결과 해석

각 LLM 응답은 다음 4분류로 기록된다.

- exact — 문자열 정규화 후 정확 일치
- approx — 상대오차 `|llm - expected| / |expected| <= 1e-4`
- wrong — 위 두 조건 모두 실패
- no_answer — 응답에서 숫자 추출 실패

SooTool 은 `REGISTRY.invoke` 결과 Decimal 을 그대로 비교하므로 원칙적으로 exact
를 유지해야 한다. 불일치 발생 시 `cases.yaml` 의 `expected_decimal_string`
또는 정책 YAML 변경을 의심하라.

## CI 제외

이 디렉토리는 CI 파이프라인에서 실행하지 않는다. `run_benchmark.py` 가 외부 API
비용과 네트워크 의존성을 가지므로 PR 검증의 결정론적 속성과 충돌한다.
관련 검증은 `tests/bench/test_cases_yaml.py` 가 로컬·CI 모두에서 cases.yaml 의
구조 무결성과 `REGISTRY` ground truth 일치만 확인한다.

## 주의

- LLM 응답의 숫자 추출 규칙은 `_NUMBER_RE` 정규식 첫 매치이다. LLM 이 서문·
  후주를 섞어 답하면 계산과 무관한 숫자가 잡힐 수 있다. 원문 응답(raw)은
  결과 파일에 함께 기록된다.
- `expected_decimal_string` 은 현 정책 YAML(`kr_income_2026.yaml`,
  `kr_capital_gains_2026.yaml`) 기준이다. 정책 변경 시 `cases.yaml` 을 재생성하라.
- Gemini 모델은 코딩 과제에 쓰지 않는다 (CLAUDE.md 금지 조항). 본 벤치는
  LLM 을 비코딩 "계산 정확성 측정 대상" 으로만 사용하므로 허용된다.
