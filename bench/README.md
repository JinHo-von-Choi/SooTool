# 계산 정확도 벤치마크

같은 계산 문제 20개를 LLM에 자연어로 묻고, SooTool 도구 결과(정답)와 비교한다. 세금 구간 경계, 반올림 규칙, 복리, 분포 함수처럼 LLM이 자주 틀리는 계산에서 정확도가 얼마나 차이 나는지 보여 주는 것이 목적이다.

LLM API를 호출하므로 비용이 들고 결과가 실행마다 달라진다. 그래서 CI에서는 돌리지 않고 필요할 때 손으로 실행한다.

## 결과

|파일|대상 모델|
|-|-|
|[results/2026-04-24-final.md](results/2026-04-24-final.md)|gpt-4o, claude-sonnet-4-5, gemini-2.5-pro|
|[results/2026-04-24-sota.md](results/2026-04-24-sota.md)|gpt-5.4, claude-opus-4-7, gemini-3-pro-preview|

## 문제 구성

|분류|개수|내용|
|-|-|-|
|tax_korea|8|소득세 구간 경계와 구간 안쪽: 과세표준 1,400만 / 5,000만 / 8,800만 / 1억2,500만 / 1억5,000만 / 3억 / 5억 / 10억|
|vat|3|부가세 역산을 DOWN, HALF_UP, HALF_EVEN으로 각각(원 단위 차이 유도)|
|finance_compound|2|월복리 120개월, 일복리 30일 미래가치|
|probability|2|이항 CDF(n=30, k=15), 정규 분위수(q=0.999)|
|stats|1|일표본 양측 t-검정 p-value|
|engineering_ac|2|RLC 직렬 임피던스, 3상 평형 전력|
|tax_korea_capgain|2|일반 부동산 양도소득세(장기보유특별공제 10년, 15년)|

문제는 `cases.yaml`에 있다. 항목마다 `id`, `prompt`(LLM에 보낼 질문), `tool_call`(정답을 낼 SooTool 호출), `expected_decimal_string`(정답), `category`, `difficulty`가 있다.

## 판정 기준

|판정|조건|
|-|-|
|exact|정규화한 문자열이 정답과 같다|
|approx|상대오차 `|응답 - 정답| / |정답|`이 0.0001(0.01%) 이하|
|wrong|위 두 조건을 모두 벗어난다|
|no_answer|응답에서 숫자를 찾지 못했다|

응답에서 숫자는 첫 번째로 나오는 숫자를 뽑는다. LLM이 설명을 붙여 답하면 계산과 무관한 숫자가 잡힐 수 있으므로 결과 파일에 원문 응답을 함께 기록한다.

## 실행

```bash
uv sync --group bench          # LLM SDK 설치(기본 의존성에는 없다)

export OPENAI_API_KEY=...      # 키가 없는 제공자는 건너뛴다
export ANTHROPIC_API_KEY=...
export GOOGLE_API_KEY=...

uv run python bench/run_benchmark.py                               # 전체 비교
uv run python bench/run_benchmark.py --out bench/results/run.md    # 결과 파일 지정
uv run python bench/run_benchmark.py --skip-llm                    # SooTool 정답만 기록(비용 없음)
```

모델은 환경변수로 바꾼다.

|환경변수|기본값|
|-|-|
|`SOOTOOL_BENCH_OPENAI_MODEL`|`gpt-4o`|
|`SOOTOOL_BENCH_ANTHROPIC_MODEL`|`claude-3-7-sonnet-latest`|
|`SOOTOOL_BENCH_GOOGLE_MODEL`|`gemini-2.5-pro`|

## 정답 관리

`expected_decimal_string`은 현재 정책 파일(`kr_income_2026.yaml`, `kr_capital_gains_2026.yaml` 등)로 계산한 값이다. 정책 값이 바뀌면 정답도 다시 만든다. `tests/bench/test_cases_yaml.py`가 CI에서 `cases.yaml`의 구조와, 정답이 현재 도구 결과와 같은지를 검사한다.
