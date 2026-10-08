---
name: sootool
description: 산수, 세금, 급여, 금융, 통계, 단위 변환처럼 숫자를 계산해야 하는 요청에서 직접 계산하지 않고 SooTool MCP 도구를 호출한다.
---

## When to invoke

수치 계산이 포함된 모든 요청에서 LLM 직접 연산 대신 SooTool 도구를 호출한다.

| Signal | Tool |
|-|-|
| Numbers + arithmetic | core.add / sub / mul / div or core.batch |
| income/capital gains/acquisition tax | tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax |
| VAT / supply amount | accounting.vat_extract / accounting.vat_add |
| NPV / IRR / PV / FV / discount rate | finance.pv / fv / npv / irr |
| Depreciation | accounting.depreciation_straight_line / declining_balance |
| Business days / holidays | datetime.add_business_days / count_business_days |
| t-test / confidence interval / p-value | stats.ttest_* / stats.ci_mean |
| Probability PDF/CDF | probability.normal_* / binomial_* / poisson_* |
| Matrix / vector operations | geometry.matrix_* / vector_* |
| Unit conversion | units.convert / units.temperature |
| Currency conversion | units.fx_convert / fx_triangulate |
| Multiple scenarios | core.batch |
| Chain previous result to next calculation | core.pipeline |
| Bond yield / duration | finance.bond_ytm / bond_duration |
| Option pricing / Greeks | finance.black_scholes |

## Active usage contract

1. Session start: call `sootool.skill_guide()` to load the trigger table.
2. Any response containing numbers must be preceded by a tool call.
3. Cite `trace` from the tool response in your answer.
4. Never compute arithmetic inline in a prompt.

## Tool routing

```
Numeric request
 ├─ tax / regulatory → tax.* or realestate.*  (year arg REQUIRED)
 ├─ VAT / accounting → accounting.*
 ├─ financial math  → finance.*
 ├─ statistics      → stats.*
 ├─ probability     → probability.*
 ├─ N scenarios     → core.batch
 ├─ chained steps   → core.pipeline
 └─ simple arith    → core.add / sub / mul / div
```

## Anti-patterns

- Do NOT write `40000000 × 0.15 = 6000000` in the prompt, call core.mul.
- Do NOT omit `year` on tax, payroll, or real estate tools that take it; the call is rejected with `invalid_arguments`. Never guess the rate instead.
- Do NOT call core.add 10 times, use core.batch instead.
- Do NOT ignore `status: "skipped"` in pipeline responses.
- Do NOT drop the `trace` or `policy_citations` when reporting tax or accounting results; they are the audit trail.

## Playbooks (abbreviated)

**payroll_to_net**: core.pipeline(mul 12 → tax.kr_income → sub net)

**vat_batch_summary**: core.batch(vat_extract x N) → core.add supply/vat totals

**loan_compare_3**: core.batch(loan_schedule x 3 rates)

**npv_sensitivity**: core.batch(npv x 9 discount rates)

**bond_yield_duration**: core.batch(bond_ytm + bond_duration)

**ab_test_full**: ttest_two_sample + ci_mean(A) + ci_mean(B)
