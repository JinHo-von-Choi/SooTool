# AGENTS.md용 SooTool 규칙

`AGENTS.md`나 에이전트 시스템 프롬프트에 구분선 아래 내용을 붙여 넣는다. 영어로 작성되어 있어 모델 종류와 관계없이 쓸 수 있다.

---

## SooTool: Deterministic Calculation Engine

SooTool performs numeric calculations with exact Decimal arithmetic and returns the formula, inputs, and intermediate steps as a `trace`.

### Mandatory pre-session action

Call `sootool.skill_guide()` at session start to internalize the trigger table.

### Trigger table, invoke immediately (never compute inline)

| Signal | Tool |
|-|-|
| Any arithmetic on 2+ numbers | core.add / sub / mul / div or core.batch |
| Tax: income / capital gains / acquisition | tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax |
| VAT extraction or addition | accounting.vat_extract / accounting.vat_add |
| Financial: NPV / IRR / PV / FV / discount | finance.npv / irr / pv / fv |
| Depreciation (straight-line / declining) | accounting.depreciation_* |
| Business day arithmetic | datetime.add_business_days / count_business_days |
| Statistical tests (t-test, CI) | stats.ttest_* / stats.ci_mean |
| Probability distributions | probability.* |
| Matrix / vector math | geometry.matrix_* / vector_* |
| Unit or temperature conversion | units.convert / units.temperature |
| FX / currency conversion | units.fx_convert / fx_triangulate |
| Multiple independent scenarios | core.batch |
| Chained calculation (A feeds B feeds C) | core.pipeline |
| Bond YTM or duration | finance.bond_ytm / bond_duration |
| Option pricing (Black-Scholes) | finance.black_scholes |
| Korean EITC (earned income tax credit) | tax.kr_eitc |
| Korean comprehensive income tax filing flow | tax.kr_comprehensive_income_tax |
| Securities transaction tax, pension income tax, vehicle tax, registration license tax | tax.kr_securities_transaction / kr_pension_income / kr_vehicle_tax / kr_registration_license_tax |
| Overtime, weekly holiday pay, minimum wage check | payroll.kr_overtime_pay / kr_weekly_holiday_pay / kr_minimum_wage_check |
| National pension benefit, income-based health premium | payroll.kr_national_pension_benefit / kr_health_income_premium |
| Gross salary from target net pay | payroll.kr_gross_from_net / core.solve_for |
| Housing subscription score | realestate.kr_subscription_score |
| US payroll tax (FICA, SECA) | tax_us.fica |

### Anti-patterns (prohibited)

- Writing computed numbers inline in the prompt (e.g., "40M × 15% = 6M") without tool verification
- Calling tax tools without the required `year` argument and guessing instead
- Calling core.add 10+ times when core.batch can parallelize all at once

### Active usage contract

1. Numeric calculation in any response MUST be preceded by a tool call.
2. The tool `trace` MUST be cited in the response.
3. If `_meta.hints[*].recommended_tool` is set, apply that tool in the next step.
4. For chained calculations, prefer core.pipeline over manual result threading.
