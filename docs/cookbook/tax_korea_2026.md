# 쿡북: 월급 350만 원 근로자의 2026년 세금

월급 3,500,000원(비과세 식대 200,000원 포함), 부양가족 본인 1명인 근로자를 예로 실수령액, 역산, 상여 세액, 연말정산, 퇴직소득세를 차례로 계산한다. 결과 값은 SooTool 0.2.0과 2026년 정책 파일로 실제 실행한 값이다. 정책 파일이 갱신되면 값이 달라질 수 있다.

```
월급 3,500,000 ─▶ ① 실수령액 ─▶ ② 연 실수령액(pipeline)
                     │
목표 300만 원 ─▶ ③ 세전 역산
상여 500만 원 ─▶ ④ 상여 원천징수
연간 합계 ───▶ ⑤ 연말정산
퇴직 5년 ────▶ ⑥ 퇴직소득세
```

다른 쿡북: [금융](finance_scenarios.md) · [전기 공학](engineering_electrical.md)

## ① 월 실수령액: payroll.kr_salary

> "월급 350만 원(식대 20만 원 포함)이면 실수령액이 얼마야?"

```json
{"tool": "payroll.kr_salary",
 "args": {"monthly_salary": "3500000", "year": 2026, "meal_allowance": "200000", "num_dependents": 1}}
```

```json
{
  "gross": "3500000",
  "non_taxable": "200000",
  "taxable": "3300000",
  "insurances": {
    "national_pension": "156750",
    "health_insurance": "118630",
    "long_term_care": "15580",
    "employment_insurance": "29700",
    "total": "320660"
  },
  "taxes": {"income_tax": "102770", "local_income_tax": "10277", "total": "113047"},
  "net": "3066293"
}
```

답변 예: 과세급여 3,300,000원에서 4대보험 320,660원과 소득세·지방소득세 113,047원을 빼면 실수령액은 3,066,293원이다.

- 연봉을 `monthly_salary`에 넣으면 안 된다. 월급을 넣는다.
- 4대보험 요율과 상·하한은 연중에 바뀐다. 특정 달의 급여를 계산하려면 `"as_of": "2026-03-15"`처럼 지급일을 준다. 생략하면 그해 마지막 시행 버전을 쓴다.

## ② 연 실수령액: core.pipeline

앞 결과를 다음 계산에 넘길 때는 숫자를 옮겨 적지 말고 `${단계id.result.필드}`로 참조한다.

```json
{"tool": "core.pipeline",
 "args": {"steps": [
   {"id": "salary",     "tool": "payroll.kr_salary",
    "args": {"monthly_salary": "3500000", "year": 2026, "meal_allowance": "200000"}},
   {"id": "annual_net", "tool": "core.mul",
    "args": {"operands": ["${salary.result.net}", "12"]}}
 ]}}
```

결과: `steps.annual_net.result.result` = `"36795516"`. 단계마다 `status`가 붙고, 앞 단계가 실패하면 뒤 단계는 `skipped`가 된다.

## ③ 세후 목표에서 세전 월급 역산: payroll.kr_gross_from_net

> "실수령액 300만 원을 받으려면 세전 월급이 얼마여야 해? 식대 20만 원은 따로 있어."

```json
{"tool": "payroll.kr_gross_from_net",
 "args": {"net_monthly": "3000000", "year": 2026, "meal_allowance": "200000"}}
```

```json
{"net_target": "3000000", "gross": "3412750", "achieved_net": "3000000", "residual": "0", "exact": true}
```

답변 예: 세전 월급 3,412,750원이면 실수령액이 정확히 3,000,000원이 된다. 목표에 따라 정확히 맞는 월급이 없을 수 있으니 `exact`와 `residual`을 확인한다. 다른 도구의 결과를 역산하려면 `core.solve_for`를 쓴다.

## ④ 상여 원천징수: payroll.kr_bonus_tax

> "상여 500만 원을 받으면 원천징수가 얼마나 돼?"

```json
{"tool": "payroll.kr_bonus_tax",
 "args": {"bonus_amount": "5000000", "monthly_salary": "3300000", "year": 2026}}
```

```json
{"method": "averaging", "payment_period_months": 12,
 "base_monthly_tax": "102770", "combined_monthly_tax": "151670", "bonus_tax": "586800"}
```

답변 예: 상여를 12개월로 나눠 월급에 더하는 방식(소득세법 제136조제1항제1호)으로 계산한 상여 소득세는 586,800원이다. `monthly_salary`에는 비과세를 뺀 과세급여를 넣는다. 지방소득세는 `tax.kr_local_income_tax`로 따로 구한다.

## ⑤ 연말정산: payroll.kr_year_end_tax_settlement

> "1년 동안 매달 102,770원씩 원천징수됐어. 연말정산하면 환급이야, 추가 납부야?"

과세급여 3,300,000원 × 12 = 39,600,000원, 기납부세액 102,770원 × 12 = 1,233,240원이다. 4대보험료 공제는 `extra_deductions`로 넣는다(320,660원 × 12 = 3,847,920원).

```json
{"tool": "payroll.kr_year_end_tax_settlement",
 "args": {"annual_gross": "39600000", "prepaid_tax": "1233240", "year": 2026,
          "extra_deductions": "3847920"}}
```

```json
{"taxable_income": "23062080.00", "computed_tax": "2199312", "tax_credit": "817200.000",
 "decided_tax": "1382112", "prepaid_tax": "1233240", "refund": "-148872", "status": "additional"}
```

답변 예: 결정세액 1,382,112원에서 기납부세액 1,233,240원을 빼면 148,872원을 추가 납부한다(`refund`가 음수면 추가 납부).

이 도구는 근로소득공제, 인적공제, 근로소득세액공제, 표준세액공제만 반영하는 간이 모델이다. 의료비·교육비·기부금·주택자금 공제는 `payroll.kr_medical_deduction` 등으로 먼저 구해 `extra_deductions`나 `extra_tax_credits`에 넣는다.

## ⑥ 퇴직소득세: payroll.kr_severance_pay

> "5년 일하고 퇴직금 1,750만 원을 받으면 퇴직소득세는?"

```json
{"tool": "payroll.kr_severance_pay",
 "args": {"severance_amount": "17500000", "service_years": "5", "year": 2026}}
```

```json
{"service_deduction": "5000000", "converted_salary": "30000000", "converted_deduction": "21200000.00",
 "converted_tax_base": "8800000.00", "converted_tax": "528000", "tax": "220000"}
```

답변 예: 근속연수공제 500만 원을 뺀 뒤 12배 환산급여 3,000만 원에서 환산급여공제 2,120만 원을 빼면 과세표준 880만 원, 환산 산출세액 528,000원이다. 이를 근속연수 비율로 되돌린 퇴직소득세는 220,000원이다. 지방소득세는 포함되지 않으므로 `tax.kr_local_income_tax(income_tax="220000")`으로 더한다.

## 답변에 인용할 것

- 결과 숫자와 함께 응답의 `policy_effective_date`, `policy_citations`(근거 조문)를 적으면 어느 시점의 어느 법령으로 계산했는지 드러난다.
- 감사가 필요하면 `_meta.integrity`를 보관해 두고 `sootool receipt verify`로 재실행 검증한다.
