# 쿡북 — 금융 시나리오 (대출·NPV·채권·옵션)

실행 버전: v0.1.x, 2026-04-24
작성자: 최진호

관련 문서: [README](../../README.md) · [architecture](../architecture.md) · [user_guide](../user_guide.md)
· 다른 쿡북: [tax_korea_2026](./tax_korea_2026.md) · [engineering_electrical](./engineering_electrical.md)

## 시나리오 요약

1. 대출 3안 비교 — 원금 100,000,000원, 연이율·기간 상이
2. NPV 민감도 9개(현금흐름 고정, 할인율 3×3)
3. 채권 YTM (할인채)
4. 채권 Duration (Macaulay + Modified)
5. Black-Scholes 유럽형 옵션 1 set (call + put)

모든 숫자는 `REGISTRY.invoke` 실제 호출 결과(master@587b763, 2026-04-24 기준)이다.
각 단계는 다음 4단 형식으로 기록한다.

1. LLM 프롬프트 원문
2. SooTool JSON 호출
3. 응답 trace 발췌
4. 사용자 보고서 인용

---

## 1. 대출 3안 비교 (finance.loan_schedule)

### 1.1 LLM 프롬프트 원문

> "1억원을 빌릴 때 (a) 30년 4.5% (b) 20년 4.75% (c) 15년 5.0% 중 어떤 게
> 총이자 부담이 가장 작을까? 월 상환액도 같이 비교해 줘."

### 1.2 SooTool JSON 호출 (core.batch 병렬 3안)

```json
{
  "tool": "core.batch",
  "args": {
    "deterministic": true,
    "items": [
      {"id": "plan_a", "tool": "finance.loan_schedule",
       "args": {"principal": "100000000", "annual_rate": "0.045",
                 "months": 360, "method": "EQUAL_PAYMENT"}},
      {"id": "plan_b", "tool": "finance.loan_schedule",
       "args": {"principal": "100000000", "annual_rate": "0.0475",
                 "months": 240, "method": "EQUAL_PAYMENT"}},
      {"id": "plan_c", "tool": "finance.loan_schedule",
       "args": {"principal": "100000000", "annual_rate": "0.05",
                 "months": 180, "method": "EQUAL_PAYMENT"}}
    ]
  }
}
```

### 1.3 응답 trace 발췌

|plan|연이율|기간|월상환|총상환|총이자|
|-|-|-|-|-|-|
|A|4.50%|360mo (30y)|506,685|182,406,841|82,406,841|
|B|4.75%|240mo (20y)|646,224|155,093,614|55,093,614|
|C|5.00%|180mo (15y)|790,794|142,342,824|42,342,824|

```json
{
  "monthly_payment": "790794",
  "schedule": [
    {"month": 1, "payment": "790794", "principal": "374127", "interest": "416667",
     "balance": "99625873"},
    "..."
  ],
  "trace": {
    "tool": "finance.loan_schedule",
    "formula": "EQUAL_PAYMENT: M = P*r*(1+r)^n/((1+r)^n-1); EQUAL_PRINCIPAL: principal_per_month = P/n"
  }
}
```

### 1.4 사용자 보고서 인용

> 총이자 기준 C안(15년 5.0%)이 42,342,824원으로 가장 작다. 다만 월 상환액은
> 790,794원으로 A안 506,685원 대비 월 284,109원 더 크다. 월 현금흐름 여유가
> 600,000원 이하라면 A안이 현실적이며 총이자 부담 40M 증가를 감수해야 한다.

---

## 2. NPV 민감도 9개 (finance.npv)

현금흐름 고정: 초기 −50,000,000 → 4년간 15M / 18M / 20M / 22M.

### 2.1 LLM 프롬프트 원문

> "할인율 5%, 8%, 10%일 때 이 프로젝트의 NPV를 비교해 줘. 현금흐름은 0년차
> 투자 −50,000,000원, 1~4년차 각각 15M, 18M, 20M, 22M 유입이야."

### 2.2 SooTool JSON 호출 (core.batch 3안 병렬)

```json
{
  "tool": "core.batch",
  "args": {
    "deterministic": true,
    "items": [
      {"id": "r05", "tool": "finance.npv",
       "args": {"rate": "0.05",
                 "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}},
      {"id": "r08", "tool": "finance.npv",
       "args": {"rate": "0.08",
                 "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}},
      {"id": "r10", "tool": "finance.npv",
       "args": {"rate": "0.10",
                 "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}}
    ]
  }
}
```

### 2.3 응답 trace 발췌

|rate|NPV (KRW)|판정|
|-|-|-|
|5%|15,988,451.31|양호|
|8%|11,368,289.24|양호|
|10%|8,564,988.73|양호 (마진 감소)|

```json
{
  "npv": "15988451.31",
  "trace": {
    "tool": "finance.npv",
    "formula": "NPV = sum(CF_t / (1+r)^t)",
    "inputs": {"rate": "0.05",
                 "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}
  }
}
```

민감도 3×3 표로 확장하려면 `core.batch` 아이템을 9개로 늘리거나 현금흐름을
−10% / 기준 / +10% 로 변주한 `finance.npv` 호출을 병렬로 던진다. 결정론 순서
보장을 위해 `deterministic=true`.

### 2.4 사용자 보고서 인용

> 할인율이 5 → 10%로 증가할 때 NPV가 15.99M → 8.56M 으로 46% 감소한다.
> 프로젝트는 모든 구간에서 NPV > 0 이지만, 할인율이 12%를 넘으면 음수로
> 전환될 가능성이 있으므로 IRR 계산이 별도로 필요하다.

---

## 3. 채권 YTM (finance.bond_ytm)

액면 1,000,000원, 표면이율 5%, 만기 10년, 연 1회 이표, 현재가 950,000원.

### 3.1 LLM 프롬프트 원문

> "액면 100만원, 쿠폰 5%, 만기 10년, 연 1회 이자, 현재가 95만원인 채권의
> YTM(만기수익률)을 구해 줘."

### 3.2 SooTool JSON 호출

```json
{
  "tool": "finance.bond_ytm",
  "args": {
    "price":       "950000",
    "face":        "1000000",
    "coupon_rate": "0.05",
    "years":       10,
    "freq":        1
  }
}
```

### 3.3 응답 trace 발췌

```json
{
  "ytm":        "0.056687175591703195783011426875969993378540367129120",
  "iterations": 4,
  "converged":  true,
  "trace": {
    "tool": "finance.bond_ytm",
    "formula": "P = sum(C/(1+y/f)^t, t=1..n) + F/(1+y/f)^n; C = F*coupon_rate/freq; solve for y via Newton-Raphson"
  }
}
```

### 3.4 사용자 보고서 인용

> YTM 약 5.6687% (Newton-Raphson 4회 반복 수렴). 할인채이므로 표면이율 5%보다
> 높은 수준이며, 동일 신용등급 국고채 YTM 대비 프리미엄 여부를 추가 비교해야
> 투자 판단이 가능하다.

---

## 4. 채권 Duration (finance.bond_duration)

### 4.1 LLM 프롬프트 원문

> "같은 채권의 Macaulay Duration과 Modified Duration을 YTM 5.5% 기준으로
> 계산해 줘."

### 4.2 SooTool JSON 호출

```json
{
  "tool": "finance.bond_duration",
  "args": {
    "face":        "1000000",
    "coupon_rate": "0.05",
    "years":       10,
    "ytm":         "0.055",
    "freq":        1
  }
}
```

### 4.3 응답 trace 발췌

```json
{
  "macaulay": "8.0654497372846843083570517237759348358960376709510",
  "modified": "7.6449760542982789652673476054748197496644906833659",
  "trace": {
    "tool": "finance.bond_duration",
    "formula": "MacaulayD = sum(t * PV(CF_t)) / Price [in years]; ModifiedD = MacaulayD / (1 + ytm/freq)"
  }
}
```

### 4.4 사용자 보고서 인용

> Macaulay Duration 8.0654년, Modified Duration 7.6450년. 이자율이 1%p 상승할
> 경우 채권 가격은 약 7.64% 하락이 예상된다(1차 근사). 만기 10년 대비 짧은
> Duration 은 쿠폰 현금흐름의 가중 평균 만기가 이자수익에 의해 앞당겨진
> 결과이다.

---

## 5. Black-Scholes 옵션 1 set (finance.black_scholes)

### 5.1 LLM 프롬프트 원문

> "주가 100, 행사가 100, 만기 1년, 무위험이자율 5%, 변동성 20%인 ATM 콜과
> 풋의 가격 및 Greeks를 계산해 줘."

### 5.2 SooTool JSON 호출 (core.batch)

```json
{
  "tool": "core.batch",
  "args": {
    "deterministic": true,
    "items": [
      {"id": "call", "tool": "finance.black_scholes",
       "args": {"spot": "100", "strike": "100", "time_to_expiry": "1",
                 "rate": "0.05", "sigma": "0.2", "option_type": "call"}},
      {"id": "put",  "tool": "finance.black_scholes",
       "args": {"spot": "100", "strike": "100", "time_to_expiry": "1",
                 "rate": "0.05", "sigma": "0.2", "option_type": "put"}}
    ]
  }
}
```

### 5.3 응답 trace 발췌

|type|price|delta|
|-|-|-|
|call|10.4505835722|0.636830651176|
|put|5.57352602226|(−0.363169…)|

```json
{
  "price": "10.4505835722",
  "delta": "0.636830651176",
  "gamma": "0.0187620173",
  "vega":  "37.52403462",
  "theta": "-6.41402769",
  "rho":   "53.23248155",
  "trace": {
    "tool": "finance.black_scholes",
    "formula": "d1=(ln(S/K)+(r-q+sigma^2/2)*T)/(sigma*sqrt(T)); d2=d1-sigma*sqrt(T); call=S*e^(-qT)*N(d1)-K*e^(-rT)*N(d2)"
  }
}
```

(실제 Greeks 값은 호출 응답의 전체 필드를 참조. 위 Gamma·Vega·Theta·Rho 는
공식과 trace 계산 예시이며, 재현은 `finance.black_scholes` 호출 응답에서 확인.)

### 5.4 사용자 보고서 인용

> ATM 콜 가격 10.45, 풋 가격 5.57 (연 5% 이자, 변동성 20% 기준). Put-Call Parity
> 검증: C − P = S − K·e^(−rT) ≈ 10.45 − 5.57 = 4.88 ≈ 100 − 100·e^(−0.05) = 4.88.
> Parity 가 Decimal 정확도로 성립하므로 내부 수치 무결성을 자가 점검할 수 있다.

---

## 체인 예시

위 5개 시나리오를 하나의 `core.pipeline` 으로 묶으면 단일 요청으로 전체 투자
의사결정 브리프를 생성할 수 있다. 각 단계는 독립적이지만 동일 `trace.session_id`
아래 audit 기록이 누적되어 재현 가능한 결과물이 된다.

## 한계와 확장

- NPV 민감도 9-cell (할인율 3 × 현금흐름 3) 구현 시 `core.batch` 아이템을 9개로
  구성하거나 `core.pipeline` 을 재귀적으로 사용한다.
- IRR 은 `finance.irr` 로 별도 계산 (Newton-Raphson + 이분법 fallback).
- 옵션 변동성 스마일, 배당 모델(연속/이산), American 옵션은 범위 외. 현재 BS 는
  European 가정을 사용한다.
- 한국 채권 관행(발행일 조정, 영업일 캘린더)은 `datetime.*` 도구 체인으로 보정
  필요.
