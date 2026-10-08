# 쿡북: 대출, 투자, 채권, 옵션

금융 계산 다섯 가지를 요청 문장, 도구 호출, 결과, 답변 예 순서로 정리한다. 결과 값은 SooTool 0.2.0에서 실제 실행한 값이다.

다른 쿡북: [한국 세금](tax_korea_2026.md) · [전기 공학](engineering_electrical.md)

## 1. 대출 3안 비교: core.batch + finance.loan_schedule

> "1억 원을 빌릴 때 (A) 30년 4.5%, (B) 20년 4.75%, (C) 15년 5.0% 중 총이자가 가장 적은 건? 월 상환액도 비교해 줘."

조건만 다른 같은 계산은 `core.batch`로 한 번에 보낸다.

```json
{"tool": "core.batch",
 "args": {"items": [
   {"id": "A", "tool": "finance.loan_schedule",
    "args": {"principal": "100000000", "annual_rate": "0.045",  "months": 360, "method": "EQUAL_PAYMENT"}},
   {"id": "B", "tool": "finance.loan_schedule",
    "args": {"principal": "100000000", "annual_rate": "0.0475", "months": 240, "method": "EQUAL_PAYMENT"}},
   {"id": "C", "tool": "finance.loan_schedule",
    "args": {"principal": "100000000", "annual_rate": "0.05",   "months": 180, "method": "EQUAL_PAYMENT"}}
 ]}}
```

각 결과에는 `monthly_payment`와 회차별 `schedule`(`payment`, `principal`, `interest`, `balance`)이 있다. 총상환액과 총이자는 `schedule`의 `payment`, `interest`를 더한 값이다(마지막 회차는 잔액을 0으로 맞추느라 금액이 조금 다르다).

|안|연이율|기간|월 상환액|총상환액|총이자|
|-|-|-|-|-|-|
|A|4.50%|30년|506,685|182,406,841|82,406,841|
|B|4.75%|20년|646,224|155,093,614|55,093,614|
|C|5.00%|15년|790,794|142,342,824|42,342,824|

답변 예: 총이자는 C안이 42,342,824원으로 가장 적다. 대신 월 상환액이 790,794원으로 A안보다 284,109원 많다.

원금균등 상환은 `"method": "EQUAL_PRINCIPAL"`이다.

## 2. 할인율별 NPV와 IRR: finance.npv, finance.irr

> "0년차에 5천만 원을 투자하고 1~4년차에 1,500만, 1,800만, 2,000만, 2,200만 원이 들어와. 할인율 5%, 8%, 10%에서 NPV는? IRR은?"

```json
{"tool": "core.batch",
 "args": {"items": [
   {"id": "r05", "tool": "finance.npv", "args": {"rate": "0.05", "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}},
   {"id": "r08", "tool": "finance.npv", "args": {"rate": "0.08", "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}},
   {"id": "r10", "tool": "finance.npv", "args": {"rate": "0.10", "cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}},
   {"id": "irr", "tool": "finance.irr", "args": {"cashflows": ["-50000000","15000000","18000000","20000000","22000000"]}}
 ]}}
```

|할인율|NPV|
|-|-|
|5%|15,988,451.31|
|8%|11,368,289.24|
|10%|8,564,988.73|

IRR: `"irr": "0.17187605..."`, `"converged": true`

답변 예: 할인율이 5%에서 10%로 오르면 NPV는 1,599만 원에서 856만 원으로 줄지만 세 경우 모두 양수다. IRR이 약 17.19%이므로 자본비용이 이보다 낮으면 투자 가치가 있다.

`finance.irr`은 해를 찾지 못하면 예외 대신 `"irr": null`, `"converged": false`를 돌려준다. 현금흐름의 부호가 한 번도 바뀌지 않으면 바로 이렇게 끝난다.

## 3. 채권 만기수익률: finance.bond_ytm

> "액면 100만 원, 표면이율 5%, 만기 10년, 연 1회 이자, 현재가 95만 원인 채권의 만기수익률은?"

```json
{"tool": "finance.bond_ytm",
 "args": {"price": "950000", "face": "1000000", "coupon_rate": "0.05", "years": 10, "freq": 1}}
```

```json
{"ytm": "0.056687175591703195783011426875969993378540367129120", "iterations": 4, "converged": true}
```

답변 예: 만기수익률은 약 5.669%다. 액면보다 싸게 사므로 표면이율 5%보다 높다.

## 4. 채권 듀레이션: finance.bond_duration

> "같은 채권의 맥컬리 듀레이션과 수정 듀레이션을 수익률 5.5% 기준으로 구해 줘."

```json
{"tool": "finance.bond_duration",
 "args": {"face": "1000000", "coupon_rate": "0.05", "years": 10, "ytm": "0.055", "freq": 1}}
```

```json
{"macaulay": "8.0654497372846843083570517237759348358960376709510",
 "modified": "7.6449760542982789652673476054748197496644906833659"}
```

답변 예: 맥컬리 듀레이션 8.065년, 수정 듀레이션 7.645다. 금리가 1%p 오르면 채권 가격은 약 7.6% 내린다(1차 근사).

## 5. 유럽형 옵션 가격과 그릭스: finance.black_scholes

> "주가 100, 행사가 100, 만기 1년, 무위험이자율 5%, 변동성 20%인 콜과 풋의 가격과 그릭스는?"

```json
{"tool": "core.batch",
 "args": {"items": [
   {"id": "call", "tool": "finance.black_scholes",
    "args": {"spot": "100", "strike": "100", "time_to_expiry": "1", "rate": "0.05", "sigma": "0.2", "option_type": "call"}},
   {"id": "put",  "tool": "finance.black_scholes",
    "args": {"spot": "100", "strike": "100", "time_to_expiry": "1", "rate": "0.05", "sigma": "0.2", "option_type": "put"}}
 ]}}
```

|구분|price|delta|gamma|vega|theta|rho|
|-|-|-|-|-|-|-|
|call|10.4505835722|0.636830651176|0.0187620173458|37.5240346917|-6.41402754644|53.2324815454|
|put|5.57352602226|-0.363169348824|0.0187620173458|37.5240346917|-1.65788042393|-41.8904609047|

답변 예: 콜 10.45, 풋 5.57이다. 콜-풋 패리티로 검산하면 C − P = 4.877이고 S − K·e^(−rT) = 100 − 100·e^(−0.05) = 4.877로 맞는다.

연속 배당이 있으면 `dividend_yield`(기본 "0")를 넘긴다. 이 도구는 유럽형 옵션만 다룬다. 미국형 옵션, 변동성 스마일은 범위 밖이다.
